"""Automated Google Colab notebook runner using Selenium.

Launches a headless Chrome browser, opens a Colab notebook from Google Drive,
clicks "Run All", monitors progress, and downloads results when complete.

Requires:
    pip install selenium webdriver-manager google-api-python-client google-auth-oauthlib

Usage:
    python colab_runner.py                          # Interactive mode
    python colab_runner.py --notebook-url URL        # Direct Colab URL
    python colab_runner.py --notebook-id DRIVE_ID    # Google Drive file ID
    python colab_runner.py --headless                # Run without visible browser
    python colab_runner.py --monitor-only            # Just watch Google Drive for results

Author: PyAgentVox
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('colab_runner')


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_NOTEBOOK_NAME = 'luna_avatar_generator.ipynb'
DRIVE_OUTPUT_FOLDER = 'luna_avatars'
LOCAL_OUTPUT_DIR = Path.home() / '.claude' / 'luna'
POLL_INTERVAL_SECONDS = 30
MAX_RUNTIME_HOURS = 6
STATUS_FILE_NAME = '_status.txt'
PROGRESS_FILE_NAME = '_progress.txt'


# ============================================================================
# SELENIUM AUTOMATION (Method 1 - Browser Automation)
# ============================================================================

class ColabBrowserAutomation:
    """Automates Colab notebook execution via Selenium browser control.

    This approach uses Selenium to:
    1. Open the Colab notebook URL in Chrome
    2. Wait for the notebook to load
    3. Click "Runtime > Run all" via keyboard shortcut
    4. Monitor execution via the Google Drive output files
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def _setup_driver(self) -> None:
        """Initialize Chrome WebDriver with appropriate options."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except ImportError:
            service = Service()

        options = Options()
        if self.headless:
            options.add_argument('--headless=new')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')

        # Persist login session across runs
        user_data_dir = Path.home() / '.colab_runner' / 'chrome_profile'
        user_data_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f'--user-data-dir={user_data_dir}')

        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)
        logger.info('Chrome WebDriver initialized (headless=%s)', self.headless)

    def _check_google_login(self) -> bool:
        """Check if we're logged into Google. If not, pause for manual login."""
        self.driver.get('https://accounts.google.com')
        time.sleep(3)

        # If we're on the accounts page with a sign-in button, we're not logged in
        if 'signin' in self.driver.current_url.lower():
            if self.headless:
                logger.error(
                    'Not logged into Google. Run once with --no-headless to log in first.\n'
                    'Your session will be saved for future headless runs.'
                )
                return False
            else:
                logger.warning(
                    'Not logged into Google. Please log in manually in the browser window.\n'
                    'Press Enter here when done...'
                )
                input()
                return True

        logger.info('Google login session found')
        return True

    def run_notebook(self, notebook_url: str) -> bool:
        """Open and execute a Colab notebook.

        Args:
            notebook_url: Full Colab notebook URL.

        Returns:
            True if notebook was triggered successfully.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        try:
            self._setup_driver()

            if not self._check_google_login():
                return False

            # Open the notebook
            logger.info('Opening notebook: %s', notebook_url)
            self.driver.get(notebook_url)

            # Wait for Colab to fully load (look for the toolbar)
            wait = WebDriverWait(self.driver, 60)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '#toolbar, .colab-toolbar, [role="toolbar"]')
            ))
            logger.info('Notebook loaded')

            # Wait a bit for full initialization
            time.sleep(5)

            # Connect to runtime first - click the "Connect" button if present
            try:
                connect_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    '#connect, .connect-button, [aria-label*="Connect"]'
                )
                connect_btn.click()
                logger.info('Clicked Connect button')
                time.sleep(10)  # Wait for runtime to connect
            except Exception:
                logger.info('No Connect button found (may already be connected)')

            # Trigger "Run all" via Ctrl+F9 keyboard shortcut
            # This is more reliable than clicking through menus
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.CONTROL + Keys.F9)
            logger.info('Sent Ctrl+F9 (Run All) keyboard shortcut')

            # Alternative: try through the Runtime menu
            time.sleep(2)
            try:
                # Click Runtime menu
                runtime_menu = self.driver.find_element(
                    By.XPATH,
                    '//div[contains(text(), "Runtime") or contains(text(), "runtime")]'
                )
                runtime_menu.click()
                time.sleep(1)

                # Click "Run all"
                run_all = self.driver.find_element(
                    By.XPATH,
                    '//div[contains(text(), "Run all")]'
                )
                run_all.click()
                logger.info('Clicked Runtime > Run All via menu')
            except Exception:
                logger.info('Menu click fallback not needed or unavailable')

            # Wait a moment for execution to begin
            time.sleep(5)

            # Check if execution started by looking for running indicators
            logger.info('Notebook execution triggered successfully')
            return True

        except Exception as e:
            logger.error('Failed to run notebook: %s', e)
            return False

    def close(self) -> None:
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None


# ============================================================================
# GOOGLE DRIVE MONITOR (Method 2 - Drive API Monitoring)
# ============================================================================

class DriveMonitor:
    """Monitors Google Drive for generation progress and downloads results.

    Uses the Google Drive API to:
    1. Watch the output folder for status updates
    2. Track progress as images are generated
    3. Download completed images to local avatar directory
    """

    def __init__(self, output_folder: str = DRIVE_OUTPUT_FOLDER):
        self.output_folder = output_folder
        self.service = None

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API using OAuth."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds_dir = Path.home() / '.colab_runner'
        creds_dir.mkdir(parents=True, exist_ok=True)
        token_path = creds_dir / 'token.json'
        creds_path = creds_dir / 'credentials.json'

        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    logger.error(
                        'No credentials.json found at %s\n'
                        'Download OAuth credentials from Google Cloud Console:\n'
                        '  1. Go to https://console.cloud.google.com/apis/credentials\n'
                        '  2. Create OAuth 2.0 Client ID (Desktop application)\n'
                        '  3. Download JSON and save as %s',
                        creds_path, creds_path,
                    )
                    sys.exit(1)

                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, 'w') as f:
                f.write(creds.to_json())

        self.service = build('drive', 'v3', credentials=creds)
        logger.info('Google Drive API authenticated')

    def _find_folder(self) -> str | None:
        """Find the output folder ID on Google Drive.

        Returns:
            Folder ID or None if not found.
        """
        results = self.service.files().list(
            q=f"name='{self.output_folder}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)',
        ).execute()

        files = results.get('files', [])
        if files:
            folder_id = files[0]['id']
            logger.info('Found Drive folder: %s (id: %s)', self.output_folder, folder_id)
            return folder_id
        return None

    def _read_drive_file(self, folder_id: str, filename: str) -> str | None:
        """Read a text file from the Drive output folder.

        Args:
            folder_id: Parent folder ID.
            filename: Name of the file to read.

        Returns:
            File contents as string, or None if not found.
        """
        from googleapiclient.http import MediaIoBaseDownload
        import io

        results = self.service.files().list(
            q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='files(id)',
        ).execute()

        files = results.get('files', [])
        if not files:
            return None

        request = self.service.files().get_media(fileId=files[0]['id'])
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue().decode('utf-8')

    def check_status(self) -> str | None:
        """Check the current generation status from Drive.

        Returns:
            Status string or None if not available.
        """
        if not self.service:
            self._authenticate()

        folder_id = self._find_folder()
        if not folder_id:
            return None

        return self._read_drive_file(folder_id, STATUS_FILE_NAME)

    def get_progress(self) -> str | None:
        """Get the progress log from Drive.

        Returns:
            Progress log string or None.
        """
        if not self.service:
            self._authenticate()

        folder_id = self._find_folder()
        if not folder_id:
            return None

        return self._read_drive_file(folder_id, PROGRESS_FILE_NAME)

    def download_results(self, local_dir: Path | None = None) -> int:
        """Download all generated images from Drive to local directory.

        Args:
            local_dir: Local directory to save images. Defaults to Luna avatar dir.

        Returns:
            Number of images downloaded.
        """
        from googleapiclient.http import MediaIoBaseDownload
        import io

        if not self.service:
            self._authenticate()

        local_dir = local_dir or LOCAL_OUTPUT_DIR

        folder_id = self._find_folder()
        if not folder_id:
            logger.error('Output folder not found on Drive')
            return 0

        # List all subfolders (outfit directories)
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)',
        ).execute()

        downloaded = 0
        for subfolder in results.get('files', []):
            outfit_name = subfolder['name']
            if outfit_name.startswith('_'):
                continue

            local_outfit_dir = local_dir / outfit_name
            local_outfit_dir.mkdir(parents=True, exist_ok=True)

            # List images in this outfit folder
            images = self.service.files().list(
                q=f"'{subfolder['id']}' in parents and name contains '.png' and trashed=false",
                spaces='drive',
                fields='files(id, name)',
            ).execute()

            for img_file in images.get('files', []):
                local_path = local_outfit_dir / img_file['name']
                if local_path.exists():
                    logger.debug('Skip (exists): %s', local_path)
                    continue

                logger.info('Downloading: %s/%s', outfit_name, img_file['name'])
                request = self.service.files().get_media(fileId=img_file['id'])
                buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(buffer, request)

                done = False
                while not done:
                    _, done = downloader.next_chunk()

                with open(local_path, 'wb') as f:
                    f.write(buffer.getvalue())

                downloaded += 1

        # Also download the config YAML
        config_content = self._read_drive_file(folder_id, '_image_config.yaml')
        if config_content:
            config_path = local_dir / '_generated_config.yaml'
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            logger.info('Config saved: %s', config_path)

        logger.info('Downloaded %d new images to %s', downloaded, local_dir)
        return downloaded


# ============================================================================
# COLAB BUILT-IN SCHEDULER (Method 3 - Zero-dependency)
# ============================================================================

def print_scheduler_instructions(notebook_url: str) -> None:
    """Print instructions for using Colab's built-in scheduler.

    This is the simplest approach and requires zero local dependencies.

    Args:
        notebook_url: URL of the notebook on Google Drive.
    """
    print(f"""
{'=' * 70}
  COLAB BUILT-IN SCHEDULER (Simplest Approach)
{'=' * 70}

  Google Colab has a native scheduling feature that can run notebooks
  automatically. Here's how to use it:

  1. Open the notebook in Colab:
     {notebook_url}

  2. Click the clock/schedule icon in the left sidebar (or go to
     Tools > Command palette > "Schedule notebook")

  3. Set the schedule:
     - For one-time run: Set to run once at a specific time
     - For batch runs: Schedule multiple runs

  4. The notebook will:
     - Auto-connect to a GPU runtime
     - Execute all cells in order
     - Save results to Google Drive
     - Create a read-only copy of the executed notebook

  5. After completion, run this script with --download to sync results:
     python colab_runner.py --download

  IMPORTANT NOTES:
  - The notebook MUST be on Google Drive (not just a Colab link)
  - You must have edited the notebook in Colab at least once
  - Free tier scheduling is limited but functional
  - Each scheduled run creates a new copy in your Drive
{'=' * 70}
""")


# ============================================================================
# JAVASCRIPT INJECTION (Method 4 - Console Automation)
# ============================================================================

def generate_js_autorun() -> str:
    """Generate JavaScript code that can be pasted into browser console.

    This is a fallback method that works by injecting JS into the Colab page.
    User pastes this into the browser's developer console (F12) and it handles
    reconnection, keep-alive, and auto-run.

    Returns:
        JavaScript code string.
    """
    return """
// === Luna Avatar Generator - Colab Auto-Runner ===
// Paste this into the browser console (F12) while the notebook is open.
// It will: click "Run All", keep the session alive, and monitor progress.

(function() {
    'use strict';

    const KEEP_ALIVE_INTERVAL_MS = 60000;  // Click reconnect every 60s
    const CHECK_INTERVAL_MS = 30000;       // Check completion every 30s

    console.log('[Luna] Auto-runner started');

    // Function to click "Run all" via the Runtime menu
    function clickRunAll() {
        // Method 1: Keyboard shortcut
        document.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'F9', code: 'F9', keyCode: 120,
            ctrlKey: true, bubbles: true
        }));
        console.log('[Luna] Sent Ctrl+F9');

        // Method 2: Click through menu (backup)
        setTimeout(() => {
            const menuItems = document.querySelectorAll(
                '.goog-menuitem-content, [role="menuitem"]'
            );
            for (const item of menuItems) {
                if (item.textContent.includes('Run all')) {
                    item.click();
                    console.log('[Luna] Clicked Run All menu item');
                    return;
                }
            }
        }, 2000);
    }

    // Keep session alive by clicking reconnect buttons
    function keepAlive() {
        // Click any "Reconnect" button that appears
        const buttons = document.querySelectorAll('button, [role="button"]');
        for (const btn of buttons) {
            const text = btn.textContent.toLowerCase();
            if (text.includes('reconnect') || text.includes('yes')) {
                btn.click();
                console.log('[Luna] Clicked reconnect/yes');
            }
        }

        // Click the connect button if disconnected
        const connectBtn = document.querySelector(
            '#connect, .connect-button'
        );
        if (connectBtn && connectBtn.textContent.toLowerCase().includes('connect')) {
            connectBtn.click();
            console.log('[Luna] Clicked connect');
        }
    }

    // Check if all cells have finished executing
    function checkCompletion() {
        const runningCells = document.querySelectorAll(
            '.running, [class*="running"], .pending'
        );
        if (runningCells.length === 0) {
            const outputs = document.querySelectorAll('.output_text, .output_area');
            for (const output of outputs) {
                if (output.textContent.includes('BATCH GENERATION COMPLETE')) {
                    console.log('[Luna] Generation complete!');
                    clearInterval(keepAliveTimer);
                    clearInterval(checkTimer);
                    alert('Luna avatar generation is COMPLETE! Check Google Drive.');
                    return;
                }
            }
        }
        console.log(`[Luna] Still running... (${runningCells.length} cells active)`);
    }

    // Start the process
    clickRunAll();

    const keepAliveTimer = setInterval(keepAlive, KEEP_ALIVE_INTERVAL_MS);
    const checkTimer = setInterval(checkCompletion, CHECK_INTERVAL_MS);

    console.log('[Luna] Timers started. Keep-alive: 60s, Check: 30s');
    console.log('[Luna] To stop: clearInterval on keepAliveTimer/checkTimer');

    // Expose for manual control
    window._lunaRunner = { keepAliveTimer, checkTimer, clickRunAll, keepAlive };
})();
"""


# ============================================================================
# MAIN CLI
# ============================================================================

def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S',
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description='Automated Google Colab runner for Luna avatar generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Methods (in order of preference):
  1. --scheduler    Use Colab's built-in scheduler (simplest, zero-dep)
  2. --browser      Selenium browser automation (requires Chrome + selenium)
  3. --javascript   Generate JS for browser console (manual paste, reliable)
  4. --monitor      Just monitor Drive + download results (any method)

Examples:
  python colab_runner.py --scheduler
  python colab_runner.py --browser --notebook-url "https://colab.research.google.com/drive/ABC123"
  python colab_runner.py --javascript > autorun.js
  python colab_runner.py --monitor --download
        """,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--scheduler', action='store_true', help='Show Colab scheduler instructions')
    mode.add_argument('--browser', action='store_true', help='Use Selenium browser automation')
    mode.add_argument('--javascript', action='store_true', help='Generate JS auto-runner code')
    mode.add_argument('--monitor', action='store_true', help='Monitor Drive for progress')
    mode.add_argument('--download', action='store_true', help='Download results from Drive')

    parser.add_argument('--notebook-url', help='Full Colab notebook URL')
    parser.add_argument('--notebook-id', help='Google Drive file ID of the notebook')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser headlessly (default)')
    parser.add_argument('--no-headless', action='store_true', help='Show the browser window (for login)')
    parser.add_argument('--output-dir', type=Path, help='Local directory for downloads')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    return parser.parse_args()


def get_notebook_url(args: argparse.Namespace) -> str:
    """Resolve the notebook URL from arguments.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Full Colab notebook URL.
    """
    if args.notebook_url:
        return args.notebook_url
    if args.notebook_id:
        return f'https://colab.research.google.com/drive/{args.notebook_id}'

    print('No notebook URL provided.')
    print('Options:')
    print('  1. Upload luna_avatar_generator.ipynb to Google Drive')
    print('  2. Open it in Colab (right-click > Open with > Google Colaboratory)')
    print('  3. Copy the URL from the browser address bar')
    print('  4. Run this script with --notebook-url URL')
    print()

    url = input('Paste notebook URL (or press Enter to skip): ').strip()
    if url:
        return url

    return ''


def main() -> None:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.debug)

    headless = args.headless and not args.no_headless

    # ── Scheduler instructions ────────────────────────────────────────
    if args.scheduler:
        url = get_notebook_url(args)
        print_scheduler_instructions(url or '<your-notebook-url>')
        return

    # ── JavaScript auto-runner ────────────────────────────────────────
    if args.javascript:
        print(generate_js_autorun())
        return

    # ── Download results ──────────────────────────────────────────────
    if args.download:
        monitor = DriveMonitor()
        count = monitor.download_results(args.output_dir)
        print(f'Downloaded {count} images')
        return

    # ── Monitor progress ──────────────────────────────────────────────
    if args.monitor:
        monitor = DriveMonitor()
        start_time = time.time()
        max_seconds = MAX_RUNTIME_HOURS * 3600

        print(f'Monitoring Google Drive for progress (max {MAX_RUNTIME_HOURS}h)...')
        print('Press Ctrl+C to stop monitoring')

        try:
            while (time.time() - start_time) < max_seconds:
                status = monitor.check_status()
                if status:
                    elapsed = time.time() - start_time
                    print(f'[{elapsed/60:.0f}m] Status: {status}')

                    if status.startswith('COMPLETE') or status == 'DONE':
                        print('\nGeneration complete! Downloading results...')
                        count = monitor.download_results(args.output_dir)
                        print(f'Downloaded {count} images')
                        return
                else:
                    print(f'[{(time.time()-start_time)/60:.0f}m] No status yet...')

                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print('\nMonitoring stopped.')
            response = input('Download any available results? [y/N]: ').strip().lower()
            if response == 'y':
                count = monitor.download_results(args.output_dir)
                print(f'Downloaded {count} images')
        return

    # ── Browser automation ────────────────────────────────────────────
    if args.browser:
        url = get_notebook_url(args)
        if not url:
            logger.error('Notebook URL required for browser automation')
            sys.exit(1)

        automation = ColabBrowserAutomation(headless=headless)
        try:
            success = automation.run_notebook(url)
            if success:
                print('\nNotebook triggered. Starting progress monitor...')
                monitor = DriveMonitor()
                start_time = time.time()

                try:
                    while (time.time() - start_time) < MAX_RUNTIME_HOURS * 3600:
                        status = monitor.check_status()
                        if status:
                            print(f'[{(time.time()-start_time)/60:.0f}m] {status}')
                            if status.startswith('COMPLETE') or status == 'DONE':
                                break
                        time.sleep(POLL_INTERVAL_SECONDS)
                except KeyboardInterrupt:
                    print('\nStopped monitoring.')

                print('\nDownloading results...')
                count = monitor.download_results(args.output_dir)
                print(f'Downloaded {count} images')
            else:
                logger.error('Failed to trigger notebook')
                sys.exit(1)
        finally:
            automation.close()
        return

    # ── Default: show help ────────────────────────────────────────────
    print(f"""
{'=' * 70}
  Luna Avatar Generator - Colab Automation Runner
{'=' * 70}

  This tool helps you run the Luna avatar generation notebook on
  Google Colab's free GPU without manual clicking.

  SETUP (one-time):
    1. Upload colab/luna_avatar_generator.ipynb to Google Drive
    2. Right-click > Open with > Google Colaboratory
    3. Copy the URL from the address bar

  METHODS (choose one):

    A) SIMPLEST - Colab's Built-in Scheduler:
       python colab_runner.py --scheduler --notebook-url URL

    B) FULLY AUTOMATED - Selenium Browser:
       pip install selenium webdriver-manager
       python colab_runner.py --browser --no-headless --notebook-url URL
       (First run with --no-headless to log in, then use --headless)

    C) SEMI-AUTOMATED - JavaScript Console:
       python colab_runner.py --javascript
       (Paste output into browser console while notebook is open)

    D) MONITOR ONLY - Watch Progress:
       pip install google-api-python-client google-auth-oauthlib
       python colab_runner.py --monitor

    E) DOWNLOAD ONLY - Get Results:
       python colab_runner.py --download

  After generation, images sync to: {LOCAL_OUTPUT_DIR}
  Then run background removal: python remove_backgrounds.py

{'=' * 70}
""")


if __name__ == '__main__':
    main()
