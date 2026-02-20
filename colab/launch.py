"""Luna Avatar Generator - Fully Automated Colab Launcher.

Single-command launcher that handles the ENTIRE workflow:
  1. Installs required dependencies (once)
  2. Authenticates with Google (opens browser once for OAuth)
  3. Uploads BASE_IMAGES, prompt_manifest.py, and notebook to Google Drive
  4. Opens notebook in Colab via Selenium (Firefox)
  5. Sets T4 GPU runtime and clicks Run All
  6. Injects keep-alive JavaScript to prevent disconnects
  7. Monitors progress via Drive API
  8. Downloads results when complete

Usage:
    python colab/launch.py                  # Full automated launch
    python colab/launch.py --upload-only    # Just upload files to Drive
    python colab/launch.py --monitor-only   # Just monitor + download
    python colab/launch.py --download-only  # Just download finished results
    python colab/launch.py --status         # Quick status check

Requirements:
    - Firefox browser (auto-detected)
    - Google account (OAuth flow opens browser once, then caches token)
    - Internet connection

Author: PyAgentVox
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger('launch')

# ============================================================================
# PATHS & CONFIG
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Local source files
BASE_IMAGES_DIR = Path.home() / '.claude' / 'luna' / 'BASE_IMAGES'
MANIFEST_FILE = SCRIPT_DIR / 'prompt_manifest.py'
NOTEBOOK_FILE = SCRIPT_DIR / 'luna_avatar_generator.ipynb'

# Google Drive target paths
DRIVE_BASE_IMAGES_FOLDER = 'BASE_IMAGES'
DRIVE_OUTPUT_FOLDER = 'luna_avatars'

# Local output
LOCAL_OUTPUT_DIR = Path.home() / '.claude' / 'luna'

# OAuth / credentials
CREDS_DIR = Path.home() / '.colab_runner'
TOKEN_PATH = CREDS_DIR / 'token.json'
CLIENT_SECRET_PATH = CREDS_DIR / 'credentials.json'

# Selenium config
FIREFOX_PATHS = [
    Path(r'C:\Program Files\Mozilla Firefox\firefox.exe'),
    Path(r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'),
    Path.home() / 'AppData' / 'Local' / 'Mozilla Firefox' / 'firefox.exe',
]
FIREFOX_PROFILE_DIR = CREDS_DIR / 'firefox_profile'
COLAB_LOAD_TIMEOUT = 120  # seconds to wait for Colab to load
COLAB_GPU_SETUP_WAIT = 15  # seconds to wait after GPU selection

# Monitoring
POLL_INTERVAL = 30  # seconds between progress checks
MAX_RUNTIME_HOURS = 13  # max monitoring time
EST_SECONDS_PER_IMAGE = 25

# Keep-alive JS
KEEP_ALIVE_JS = r"""
(function() {
    'use strict';
    const KA = 60000, CHK = 30000;
    console.log('[Luna] Auto-runner started');
    function keepAlive() {
        document.querySelectorAll('button, [role="button"]').forEach(b => {
            const t = b.textContent.toLowerCase();
            if (t.includes('reconnect') || (t.includes('yes') && t.length < 10))
                { b.click(); console.log('[Luna] Reconnected'); }
        });
        const c = document.querySelector('#connect, .connect-button');
        if (c && c.textContent.toLowerCase().includes('connect'))
            { c.click(); console.log('[Luna] Clicked connect'); }
    }
    function checkDone() {
        const running = document.querySelectorAll('.running, [class*="running"], .pending');
        document.querySelectorAll('.output_text, .output_area').forEach(o => {
            if (o.textContent.includes('BATCH GENERATION COMPLETE') || o.textContent.includes('BATCH COMPLETE')) {
                console.log('[Luna] COMPLETE!');
                clearInterval(ka); clearInterval(ch);
                document.title = 'DONE - Luna Generator';
            }
        });
        console.log('[Luna] Active cells: ' + running.length);
    }
    const ka = setInterval(keepAlive, KA);
    const ch = setInterval(checkDone, CHK);
    window._lunaRunner = {ka, ch, keepAlive};
    console.log('[Luna] Timers active');
})();
"""


# ============================================================================
# DEPENDENCY INSTALLER
# ============================================================================

REQUIRED_PACKAGES = {
    'selenium': 'selenium',
    'webdriver_manager': 'webdriver-manager',
    'google.oauth2': 'google-auth',
    'google_auth_oauthlib': 'google-auth-oauthlib',
    'googleapiclient': 'google-api-python-client',
    'google.auth.transport.requests': 'google-auth-httplib2',
}


def _check_import(module_name: str) -> bool:
    """Check if a module is importable."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def ensure_dependencies() -> None:
    """Install any missing dependencies via pip."""
    missing = []
    for module, package in REQUIRED_PACKAGES.items():
        if not _check_import(module):
            missing.append(package)

    if not missing:
        logger.info('All dependencies installed')
        return

    logger.info('Installing missing packages: %s', ', '.join(missing))
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', '-q'] + missing,
        stdout=subprocess.DEVNULL,
    )
    logger.info('Dependencies installed successfully')


# ============================================================================
# GOOGLE DRIVE API
# ============================================================================

class DriveUploader:
    """Handles Google Drive OAuth and file uploads."""

    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive',
    ]

    def __init__(self):
        self.service = None

    def authenticate(self) -> None:
        """Authenticate with Google Drive via OAuth.

        First run opens a browser for consent. Token is cached for future runs.
        """
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        CREDS_DIR.mkdir(parents=True, exist_ok=True)
        creds = None

        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info('Refreshing expired token...')
                creds.refresh(Request())
            else:
                if not CLIENT_SECRET_PATH.exists():
                    _print_oauth_setup_instructions()
                    sys.exit(1)

                from google_auth_oauthlib.flow import InstalledAppFlow
                logger.info('Opening browser for Google OAuth consent...')
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRET_PATH), self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info('OAuth consent completed')

            with open(TOKEN_PATH, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())

        self.service = build('drive', 'v3', credentials=creds)
        logger.info('Google Drive API authenticated')

    def _find_or_create_folder(self, name: str, parent_id: str | None = None) -> str:
        """Find a folder by name, or create it if it doesn't exist.

        Args:
            name: Folder name.
            parent_id: Parent folder ID (None for root).

        Returns:
            Folder ID.
        """
        q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            q += f" and '{parent_id}' in parents"

        results = self.service.files().list(q=q, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])

        if files:
            return files[0]['id']

        # Create folder
        metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
        }
        if parent_id:
            metadata['parents'] = [parent_id]

        folder = self.service.files().create(body=metadata, fields='id').execute()
        logger.info('Created Drive folder: %s', name)
        return folder['id']

    def _upload_file(self, local_path: Path, parent_id: str, mime_type: str | None = None) -> str:
        """Upload a file to Drive, replacing if it already exists.

        Args:
            local_path: Local file path.
            parent_id: Parent folder ID on Drive.
            mime_type: MIME type (auto-detected if None).

        Returns:
            File ID on Drive.
        """
        from googleapiclient.http import MediaFileUpload

        if mime_type is None:
            ext = local_path.suffix.lower()
            mime_map = {
                '.py': 'text/x-python',
                '.ipynb': 'application/json',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
            }
            mime_type = mime_map.get(ext, 'application/octet-stream')

        name = local_path.name

        # Check if file already exists
        q = f"name='{name}' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(q=q, spaces='drive', fields='files(id)').execute()
        existing = results.get('files', [])

        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

        if existing:
            # Update existing file
            file_id = existing[0]['id']
            self.service.files().update(fileId=file_id, media_body=media).execute()
            logger.debug('Updated: %s', name)
            return file_id
        else:
            # Create new file
            metadata = {'name': name, 'parents': [parent_id]}
            result = self.service.files().create(body=metadata, media_body=media, fields='id').execute()
            logger.debug('Uploaded: %s', name)
            return result['id']

    def upload_base_images(self) -> str:
        """Upload the BASE_IMAGES folder to Drive root.

        Returns:
            Folder ID of BASE_IMAGES on Drive.
        """
        if not BASE_IMAGES_DIR.exists():
            logger.error('BASE_IMAGES directory not found: %s', BASE_IMAGES_DIR)
            sys.exit(1)

        folder_id = self._find_or_create_folder(DRIVE_BASE_IMAGES_FOLDER)

        images = sorted(BASE_IMAGES_DIR.iterdir())
        image_files = [f for f in images if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')]

        logger.info('Uploading %d base images to Drive/%s...', len(image_files), DRIVE_BASE_IMAGES_FOLDER)
        for i, img in enumerate(image_files, 1):
            self._upload_file(img, folder_id)
            if i % 5 == 0 or i == len(image_files):
                logger.info('  [%d/%d] %s', i, len(image_files), img.name)

        return folder_id

    def upload_manifest(self) -> str:
        """Upload prompt_manifest.py to Drive root.

        Returns:
            File ID on Drive.
        """
        if not MANIFEST_FILE.exists():
            logger.error('prompt_manifest.py not found: %s', MANIFEST_FILE)
            sys.exit(1)

        logger.info('Uploading prompt_manifest.py...')
        # Upload to root (the notebook searches both root and colab/)
        return self._upload_file(MANIFEST_FILE, 'root')

    def upload_notebook(self) -> str:
        """Upload the notebook to Drive root.

        Returns:
            File ID on Drive.
        """
        if not NOTEBOOK_FILE.exists():
            logger.error('Notebook not found: %s', NOTEBOOK_FILE)
            sys.exit(1)

        logger.info('Uploading luna_avatar_generator.ipynb...')
        return self._upload_file(NOTEBOOK_FILE, 'root')

    def upload_all(self) -> str:
        """Upload everything needed for the generation run.

        Returns:
            Notebook file ID on Drive.
        """
        self.upload_base_images()
        self.upload_manifest()
        notebook_id = self.upload_notebook()
        logger.info('All files uploaded to Google Drive')
        return notebook_id

    def check_status(self) -> str | None:
        """Check the generation status from Drive.

        Returns:
            Status string or None.
        """
        folder_id = self._find_or_create_folder(DRIVE_OUTPUT_FOLDER)
        q = f"name='_status.txt' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=q, spaces='drive', fields='files(id)').execute()
        files = results.get('files', [])
        if not files:
            return None

        from googleapiclient.http import MediaIoBaseDownload
        request = self.service.files().get_media(fileId=files[0]['id'])
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue().decode('utf-8').strip()

    def count_generated_images(self) -> int:
        """Count generated images on Drive.

        Returns:
            Number of PNG files in the output folder.
        """
        folder_id = self._find_or_create_folder(DRIVE_OUTPUT_FOLDER)
        count = 0

        # List subfolders
        q = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()

        for subfolder in results.get('files', []):
            if subfolder['name'].startswith('_'):
                continue
            q = f"'{subfolder['id']}' in parents and name contains '.png' and trashed=false"
            imgs = self.service.files().list(q=q, spaces='drive', fields='files(id)').execute()
            count += len(imgs.get('files', []))

        return count

    def download_results(self, local_dir: Path | None = None) -> int:
        """Download all generated images from Drive.

        Args:
            local_dir: Local directory for images. Defaults to Luna avatar dir.

        Returns:
            Number of new images downloaded.
        """
        from googleapiclient.http import MediaIoBaseDownload

        local_dir = local_dir or LOCAL_OUTPUT_DIR
        folder_id = self._find_or_create_folder(DRIVE_OUTPUT_FOLDER)

        # List subfolders
        q = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()

        downloaded = 0
        for subfolder in results.get('files', []):
            if subfolder['name'].startswith('_'):
                continue

            outfit_dir = local_dir / subfolder['name']
            outfit_dir.mkdir(parents=True, exist_ok=True)

            q = f"'{subfolder['id']}' in parents and name contains '.png' and trashed=false"
            imgs = self.service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()

            for img_file in imgs.get('files', []):
                local_path = outfit_dir / img_file['name']
                if local_path.exists():
                    continue

                logger.info('Downloading: %s/%s', subfolder['name'], img_file['name'])
                request = self.service.files().get_media(fileId=img_file['id'])
                buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(buffer, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

                with open(local_path, 'wb') as f:
                    f.write(buffer.getvalue())
                downloaded += 1

        # Download config YAML
        q = f"name='_image_config.yaml' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=q, spaces='drive', fields='files(id)').execute()
        cfg_files = results.get('files', [])
        if cfg_files:
            request = self.service.files().get_media(fileId=cfg_files[0]['id'])
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            cfg_path = local_dir / '_generated_config.yaml'
            with open(cfg_path, 'w', encoding='utf-8') as f:
                f.write(buffer.getvalue().decode('utf-8'))

        logger.info('Downloaded %d new images to %s', downloaded, local_dir)
        return downloaded


# ============================================================================
# SELENIUM BROWSER AUTOMATION (Firefox)
# ============================================================================

class ColabAutomation:
    """Automates Colab notebook execution via Firefox + Selenium."""

    def __init__(self):
        self.driver = None

    def _find_firefox(self) -> Path:
        """Find Firefox executable on this system."""
        for path in FIREFOX_PATHS:
            if path.exists():
                return path
        logger.error('Firefox not found. Checked: %s', [str(p) for p in FIREFOX_PATHS])
        sys.exit(1)

    def _setup_driver(self) -> None:
        """Initialize Firefox WebDriver."""
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service

        try:
            from webdriver_manager.firefox import GeckoDriverManager
            service = Service(GeckoDriverManager().install())
        except Exception:
            # Fall back to system geckodriver
            service = Service()

        firefox_path = self._find_firefox()
        options = Options()
        options.binary_location = str(firefox_path)

        # Use persistent profile to keep Google login session
        FIREFOX_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        options.profile = str(FIREFOX_PROFILE_DIR)

        # Large window for Colab UI
        options.add_argument('--width=1920')
        options.add_argument('--height=1080')

        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.implicitly_wait(10)
        logger.info('Firefox WebDriver initialized')

    def _ensure_google_login(self) -> bool:
        """Check Google login state. Prompt for manual login if needed."""
        self.driver.get('https://accounts.google.com')
        time.sleep(4)

        url = self.driver.current_url.lower()
        if 'signin' in url or 'servicelogin' in url:
            logger.warning(
                '\n'
                '  ==========================================\n'
                '  GOOGLE LOGIN REQUIRED\n'
                '  ==========================================\n'
                '  A Firefox window has opened.\n'
                '  Please log into your Google account there.\n'
                '  \n'
                '  Your session will be saved for future runs\n'
                '  (no login needed next time).\n'
                '  ==========================================\n'
            )
            input('  Press ENTER here after you have logged in... ')

            # Verify login succeeded
            self.driver.get('https://accounts.google.com')
            time.sleep(3)
            url = self.driver.current_url.lower()
            if 'signin' in url or 'servicelogin' in url:
                logger.error('Login failed. Please try again.')
                return False

        logger.info('Google login confirmed')
        return True

    def _open_notebook(self, notebook_id: str) -> bool:
        """Open the notebook in Colab."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        colab_url = f'https://colab.research.google.com/drive/{notebook_id}'
        logger.info('Opening Colab notebook: %s', colab_url)
        self.driver.get(colab_url)

        # Wait for Colab to load - look for the code editor or toolbar
        try:
            wait = WebDriverWait(self.driver, COLAB_LOAD_TIMEOUT)
            wait.until(lambda d: d.execute_script(
                'return document.querySelector("colab-toolbar") !== null '
                '|| document.querySelector("#toolbar") !== null '
                '|| document.querySelector(".colab-main-content") !== null '
                '|| document.querySelector("div.codecell-input-output") !== null'
            ))
            logger.info('Colab notebook loaded')
            time.sleep(5)  # Extra settle time
            return True
        except Exception as e:
            logger.error('Colab failed to load within %ds: %s', COLAB_LOAD_TIMEOUT, e)
            return False

    def _set_gpu_runtime(self) -> None:
        """Attempt to change runtime to T4 GPU via Colab menu."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait

        logger.info('Setting T4 GPU runtime...')

        # Method: Use keyboard shortcut to open command palette, then search for "Change runtime type"
        # Colab's command palette: Ctrl+Shift+P
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')

            # Try clicking Runtime menu
            runtime_menus = self.driver.find_elements(By.XPATH,
                '//div[contains(@class, "menu") and .//span[text()="Runtime"]]'
                '|//div[contains(@class, "goog-control") and contains(text(), "Runtime")]'
                '|//span[text()="Runtime"]/parent::*'
            )

            if runtime_menus:
                runtime_menus[0].click()
                time.sleep(1)

                # Click "Change runtime type"
                change_items = self.driver.find_elements(By.XPATH,
                    '//div[contains(text(), "Change runtime type")]'
                    '|//span[contains(text(), "Change runtime type")]'
                )
                if change_items:
                    change_items[0].click()
                    time.sleep(2)

                    # Look for GPU selector in the dialog
                    selectors = self.driver.find_elements(By.XPATH,
                        '//select | //div[contains(@class, "select")]'
                        '|//md-select | //mat-select'
                    )
                    for sel in selectors:
                        try:
                            # Click to open dropdown
                            sel.click()
                            time.sleep(1)

                            # Look for T4 GPU option
                            t4_options = self.driver.find_elements(By.XPATH,
                                '//option[contains(text(), "T4")]'
                                '|//li[contains(text(), "T4")]'
                                '|//div[contains(text(), "T4")]'
                                '|//md-option[contains(text(), "T4")]'
                                '|//mat-option[contains(text(), "T4")]'
                            )
                            if t4_options:
                                t4_options[0].click()
                                time.sleep(1)
                                logger.info('Selected T4 GPU')
                                break
                        except Exception:
                            continue

                    # Click Save button
                    save_btns = self.driver.find_elements(By.XPATH,
                        '//button[contains(text(), "Save")]'
                        '|//div[contains(@class, "ok-button")]'
                    )
                    if save_btns:
                        save_btns[0].click()
                        logger.info('Saved runtime settings')
                        time.sleep(COLAB_GPU_SETUP_WAIT)
                    else:
                        # Press Escape to close dialog
                        body.send_keys(Keys.ESCAPE)
                        logger.warning('Could not find Save button in runtime dialog')
                else:
                    body.send_keys(Keys.ESCAPE)
                    logger.warning('Could not find "Change runtime type" menu item')
            else:
                logger.warning(
                    'Could not find Runtime menu. GPU may need to be set manually.\n'
                    '  Go to: Runtime > Change runtime type > T4 GPU'
                )

        except Exception as e:
            logger.warning('GPU auto-selection failed: %s. Please set manually if needed.', e)

    def _click_run_all(self) -> bool:
        """Trigger "Run All" via Ctrl+F9."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        logger.info('Triggering Run All (Ctrl+F9)...')
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.CONTROL + Keys.F9)
            time.sleep(3)
            logger.info('Sent Ctrl+F9 - Run All triggered')
            return True
        except Exception as e:
            logger.error('Failed to send Ctrl+F9: %s', e)
            return False

    def _inject_keepalive(self) -> None:
        """Inject the keep-alive JavaScript into the Colab page."""
        logger.info('Injecting keep-alive JavaScript...')
        try:
            self.driver.execute_script(KEEP_ALIVE_JS)
            logger.info('Keep-alive JS injected successfully')
        except Exception as e:
            logger.warning('Failed to inject keep-alive JS: %s', e)

    def _handle_connect_dialog(self) -> None:
        """Handle any 'Connect to runtime' dialog that may appear."""
        from selenium.webdriver.common.by import By

        try:
            # Look for connect/OK buttons in dialogs
            buttons = self.driver.find_elements(By.XPATH,
                '//button[contains(text(), "OK")]'
                '|//button[contains(text(), "Connect")]'
                '|//paper-button[contains(text(), "OK")]'
            )
            for btn in buttons:
                if btn.is_displayed():
                    btn.click()
                    logger.info('Clicked dialog button: %s', btn.text)
                    time.sleep(2)
        except Exception:
            pass

    def launch(self, notebook_id: str) -> bool:
        """Full launch sequence: open, configure GPU, run all, inject keepalive.

        Args:
            notebook_id: Google Drive file ID of the notebook.

        Returns:
            True if launch was successful.
        """
        try:
            self._setup_driver()

            if not self._ensure_google_login():
                return False

            if not self._open_notebook(notebook_id):
                return False

            # Handle any initial connect dialogs
            self._handle_connect_dialog()

            # Try to set GPU runtime
            self._set_gpu_runtime()

            # Handle connect dialogs again (runtime change may trigger one)
            time.sleep(3)
            self._handle_connect_dialog()

            # Run All
            if not self._click_run_all():
                return False

            # Handle any "are you sure" dialogs
            time.sleep(2)
            self._handle_connect_dialog()

            # Inject keep-alive
            time.sleep(5)
            self._inject_keepalive()

            logger.info(
                '\n'
                '  ==========================================\n'
                '  NOTEBOOK LAUNCHED SUCCESSFULLY\n'
                '  ==========================================\n'
                '  The notebook is now running in Firefox.\n'
                '  Keep this browser window open!\n'
                '  \n'
                '  The keep-alive script will auto-reconnect\n'
                '  if the session drops.\n'
                '  ==========================================\n'
            )
            return True

        except Exception as e:
            logger.error('Launch failed: %s', e)
            return False

    def close(self) -> None:
        """Close the browser (only call when generation is fully complete)."""
        if self.driver:
            self.driver.quit()
            self.driver = None


# ============================================================================
# PROGRESS MONITOR
# ============================================================================

class ProgressMonitor:
    """Monitors generation progress via Drive API."""

    def __init__(self, drive: DriveUploader):
        self.drive = drive
        self.start_time = time.time()
        self.last_count = 0

    def check(self) -> dict:
        """Check current progress.

        Returns:
            Dict with status, count, elapsed, eta.
        """
        status = self.drive.check_status()
        count = self.drive.count_generated_images()
        elapsed = time.time() - self.start_time

        # Calculate ETA
        eta_str = '?'
        if count > self.last_count and count > 0:
            rate = elapsed / count  # seconds per image
            remaining = (4870 - count) * rate
            eta = datetime.now() + timedelta(seconds=remaining)
            eta_str = eta.strftime('%H:%M')

        result = {
            'status': status or 'UNKNOWN',
            'count': count,
            'elapsed_min': elapsed / 60,
            'eta': eta_str,
            'rate': f'{count / (elapsed / 3600):.0f}/hr' if elapsed > 60 and count > 0 else '?',
        }

        self.last_count = count
        return result

    def is_complete(self, status: str | None) -> bool:
        """Check if generation is finished."""
        if not status:
            return False
        s = status.upper()
        return s.startswith('COMPLETE') or s == 'DONE'


# ============================================================================
# OAUTH SETUP INSTRUCTIONS
# ============================================================================

def _print_oauth_setup_instructions() -> None:
    """Print instructions for setting up Google OAuth credentials."""
    print(f"""
{'=' * 70}
  GOOGLE OAUTH SETUP REQUIRED (one-time)
{'=' * 70}

  To upload files and monitor progress, this tool needs Google Drive API
  access via OAuth. Here's how to set it up:

  1. Go to: https://console.cloud.google.com/apis/credentials
     (Create a project if you don't have one)

  2. Click "+ CREATE CREDENTIALS" > "OAuth client ID"
     - Application type: "Desktop app"
     - Name: "Luna Avatar Generator" (or anything)
     - Click "Create"

  3. Download the JSON file (click the download icon)

  4. Save it as:
     {CLIENT_SECRET_PATH}

  5. Enable the Google Drive API:
     https://console.cloud.google.com/apis/library/drive.googleapis.com
     Click "Enable"

  6. Run this script again. It will open your browser for consent.

  NOTE: The OAuth consent screen may show "unverified app" warning.
  Click "Advanced" > "Go to Luna Avatar Generator (unsafe)" to proceed.
  This is normal for personal-use OAuth apps.
{'=' * 70}
""")


# ============================================================================
# MAIN CLI
# ============================================================================

def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(levelname)-7s %(message)s',
        datefmt='%H:%M:%S',
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description='Luna Avatar Generator - Fully Automated Colab Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python colab/launch.py                   Full automated launch
  python colab/launch.py --upload-only     Just upload files to Drive
  python colab/launch.py --monitor-only    Just monitor and download
  python colab/launch.py --download-only   Just download finished results
  python colab/launch.py --status          Quick status check
        """,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--upload-only', action='store_true', help='Just upload files to Google Drive')
    mode.add_argument('--monitor-only', action='store_true', help='Just monitor progress and download results')
    mode.add_argument('--download-only', action='store_true', help='Just download finished results from Drive')
    mode.add_argument('--status', action='store_true', help='Quick status check')

    parser.add_argument('--notebook-id', help='Drive file ID of notebook (auto-detected if uploaded)')
    parser.add_argument('--skip-upload', action='store_true', help='Skip file upload (files already on Drive)')
    parser.add_argument('--skip-browser', action='store_true', help='Skip browser launch (already running)')
    parser.add_argument('--output-dir', type=Path, help='Local directory for downloaded images')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    return parser.parse_args()


def run_full_launch(args: argparse.Namespace) -> None:
    """Execute the full automated launch sequence."""
    drive = DriveUploader()
    drive.authenticate()

    # Phase 1: Upload files
    notebook_id = args.notebook_id
    if not args.skip_upload:
        print('\n--- Phase 1: Uploading files to Google Drive ---')
        notebook_id = drive.upload_all()
        print(f'Notebook ID: {notebook_id}')
    elif not notebook_id:
        logger.error('--skip-upload requires --notebook-id')
        sys.exit(1)

    # Phase 2: Launch in browser
    colab = None
    if not args.skip_browser:
        print('\n--- Phase 2: Launching Colab in Firefox ---')
        colab = ColabAutomation()
        success = colab.launch(notebook_id)
        if not success:
            logger.error('Browser launch failed. Try manually or use --skip-browser')
            if colab:
                colab.close()
            sys.exit(1)
    else:
        print('\n--- Phase 2: Skipping browser launch (--skip-browser) ---')

    # Phase 3: Monitor progress
    print('\n--- Phase 3: Monitoring progress ---')
    print(f'Polling every {POLL_INTERVAL}s. Press Ctrl+C to stop monitoring.\n')
    monitor = ProgressMonitor(drive)

    try:
        while True:
            progress = monitor.check()
            status_line = (
                f'[{progress["elapsed_min"]:.0f}m] '
                f'Status: {progress["status"]} | '
                f'Images: {progress["count"]}/4870 | '
                f'Rate: {progress["rate"]} | '
                f'ETA: {progress["eta"]}'
            )
            print(status_line)

            if monitor.is_complete(progress['status']):
                print('\nGeneration COMPLETE!')
                break

            if progress['elapsed_min'] > MAX_RUNTIME_HOURS * 60:
                print(f'\nMax runtime ({MAX_RUNTIME_HOURS}h) reached. Stopping monitor.')
                break

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print('\nMonitoring stopped by user.')

    # Phase 4: Download results
    print('\n--- Phase 4: Downloading results ---')
    output_dir = args.output_dir or LOCAL_OUTPUT_DIR
    count = drive.download_results(output_dir)
    print(f'Downloaded {count} new images to {output_dir}')

    # Keep browser open but inform user
    if colab and colab.driver:
        print(
            '\nThe Firefox window is still open (generation may still be running).\n'
            'Close it manually when done, or press Ctrl+C.'
        )
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            colab.close()
            print('Browser closed.')


def main() -> None:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.debug)

    # Always ensure dependencies first
    ensure_dependencies()

    drive = DriveUploader()

    # ── Status check ──────────────────────────────────────────────────
    if args.status:
        drive.authenticate()
        status = drive.check_status()
        count = drive.count_generated_images()
        print(f'Status: {status or "No status file found"}')
        print(f'Images on Drive: {count}/4870')
        return

    # ── Upload only ───────────────────────────────────────────────────
    if args.upload_only:
        drive.authenticate()
        notebook_id = drive.upload_all()
        print(f'\nAll files uploaded to Google Drive.')
        print(f'Notebook ID: {notebook_id}')
        print(f'Colab URL: https://colab.research.google.com/drive/{notebook_id}')
        return

    # ── Download only ─────────────────────────────────────────────────
    if args.download_only:
        drive.authenticate()
        output_dir = args.output_dir or LOCAL_OUTPUT_DIR
        count = drive.download_results(output_dir)
        print(f'Downloaded {count} new images to {output_dir}')
        return

    # ── Monitor only ──────────────────────────────────────────────────
    if args.monitor_only:
        drive.authenticate()
        monitor = ProgressMonitor(drive)
        print(f'Monitoring progress. Press Ctrl+C to stop.\n')

        try:
            while True:
                progress = monitor.check()
                print(
                    f'[{progress["elapsed_min"]:.0f}m] '
                    f'{progress["status"]} | '
                    f'{progress["count"]}/4870 images | '
                    f'{progress["rate"]} | '
                    f'ETA: {progress["eta"]}'
                )

                if monitor.is_complete(progress['status']):
                    print('\nComplete! Downloading...')
                    output_dir = args.output_dir or LOCAL_OUTPUT_DIR
                    count = drive.download_results(output_dir)
                    print(f'Downloaded {count} new images')
                    return

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print('\nStopped. Use --download-only to grab results later.')
        return

    # ── Full launch (default) ─────────────────────────────────────────
    run_full_launch(args)


if __name__ == '__main__':
    main()
