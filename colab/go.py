"""Luna Avatar Generator - Zero-Setup Colab Launcher.

Fully automated launcher using ONLY Firefox + Selenium. No OAuth credentials,
no Google Cloud Console setup, no API keys. Just Firefox and a Google account.

Usage:
    python colab/go.py              # Full launch (upload + run + monitor)
    python colab/go.py --run-only   # Skip upload (files already on Drive)

How it works:
    1. Opens Firefox with persistent profile (saves your Google login)
    2. Navigates to Google Drive and uploads files via Selenium
    3. Opens the notebook in Google Colab
    4. Sets T4 GPU runtime
    5. Clicks Run All
    6. Injects keep-alive JavaScript
    7. Monitors progress by reading Colab cell output

First run: You'll need to log into Google in the Firefox window.
           After that, your session is saved -- no login needed next time.

Author: PyAgentVox
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

logger = logging.getLogger('go')

# ============================================================================
# PATHS
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_IMAGES_DIR = Path.home() / '.claude' / 'luna' / 'BASE_IMAGES'
MANIFEST_FILE = SCRIPT_DIR / 'prompt_manifest.py'
NOTEBOOK_FILE = SCRIPT_DIR / 'luna_avatar_generator.ipynb'

BROWSER_PROFILE_DIR = Path.home() / '.colab_runner' / 'firefox_profile'
GECKODRIVER_CACHE = Path.home() / '.wdm'

FIREFOX_PATHS = [
    Path(r'C:\Program Files\Mozilla Firefox\firefox.exe'),
    Path(r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'),
]

# Try to use existing Firefox profile for active Google login session
_FIREFOX_PROFILES_DIR = Path.home() / 'AppData' / 'Roaming' / 'Mozilla' / 'Firefox' / 'Profiles'

# Colab timing
PAGE_LOAD_WAIT = 8
COLAB_FULL_LOAD_WAIT = 30
CELL_RUN_CHECK_INTERVAL = 10
UPLOAD_WAIT_PER_FILE = 3
UPLOAD_BATCH_WAIT = 15

# Keep-alive JS -- handles reconnection and completion detection
KEEP_ALIVE_JS = """
(function() {
    'use strict';
    console.log('[Luna] Keep-alive started');
    function keepAlive() {
        document.querySelectorAll('button, [role="button"]').forEach(function(b) {
            var t = b.textContent.toLowerCase();
            if (t.includes('reconnect') || (t === 'ok') || (t === 'yes')) {
                b.click();
                console.log('[Luna] Auto-clicked: ' + t);
            }
        });
        var c = document.querySelector('#connect, .connect-button, colab-connect-button');
        if (c) {
            var txt = (c.textContent || c.innerText || '').toLowerCase();
            if (txt.includes('reconnect') || txt.includes('connect')) {
                c.click();
                console.log('[Luna] Reconnected runtime');
            }
        }
    }
    setInterval(keepAlive, 60000);
    keepAlive();
    console.log('[Luna] Keep-alive active (60s interval)');
})();
"""


# ============================================================================
# BROWSER SETUP
# ============================================================================

def _find_firefox() -> str:
    """Find Firefox executable."""
    for p in FIREFOX_PATHS:
        if p.exists():
            return str(p)
    # Try PATH
    for d in os.environ.get('PATH', '').split(os.pathsep):
        p = Path(d) / 'firefox.exe'
        if p.exists():
            return str(p)
    print('ERROR: Firefox not found. Install Firefox to continue.')
    sys.exit(1)


def _find_firefox_profile() -> str | None:
    """Find existing Firefox profile with Google login session."""
    if _FIREFOX_PROFILES_DIR.exists():
        # Prefer 'default-release' profile (main user profile)
        for p in sorted(_FIREFOX_PROFILES_DIR.iterdir()):
            if p.is_dir() and 'default-release' in p.name:
                logger.info('Found Firefox profile: %s', p.name)
                return str(p)
        # Fall back to any profile
        for p in sorted(_FIREFOX_PROFILES_DIR.iterdir()):
            if p.is_dir() and 'default' in p.name:
                logger.info('Found Firefox profile: %s', p.name)
                return str(p)
    return None


def create_driver():
    """Create a Firefox WebDriver with persistent profile."""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from webdriver_manager.firefox import GeckoDriverManager

    firefox_path = _find_firefox()
    logger.info('Firefox: %s', firefox_path)

    # Download/cache geckodriver
    service = Service(GeckoDriverManager().install())

    options = Options()
    options.binary_location = firefox_path

    # Try existing profile first (may have Google login), fall back to fresh profile
    existing_profile = _find_firefox_profile()
    if existing_profile:
        logger.info('Using existing Firefox profile (may have Google login)')
        options.profile = existing_profile
    else:
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        options.profile = str(BROWSER_PROFILE_DIR)

    # Window size
    options.add_argument('--width=1400')
    options.add_argument('--height=1000')

    # Set download preferences for later result downloading
    options.set_preference('browser.download.folderList', 2)
    options.set_preference('browser.download.dir', str(Path.home() / '.claude' / 'luna'))
    options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/zip,application/octet-stream')

    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    logger.info('Firefox WebDriver ready')
    return driver


# ============================================================================
# GOOGLE LOGIN CHECK
# ============================================================================

def ensure_google_login(driver) -> bool:
    """Check Google login. If not logged in, wait for user to log in."""
    logger.info('Checking Google login...')
    driver.get('https://drive.google.com')
    time.sleep(PAGE_LOAD_WAIT)

    # If redirected to login page
    url = driver.current_url.lower()
    if 'accounts.google.com' in url or 'signin' in url or 'servicelogin' in url:
        print()
        print('=' * 60)
        print('  GOOGLE LOGIN REQUIRED (one-time)')
        print('=' * 60)
        print()
        print('  A Firefox window has opened on the Google login page.')
        print('  Please log into your Google account there.')
        print()
        print('  Your login will be SAVED for future runs.')
        print('  (You will NOT need to log in again next time.)')
        print()
        print('=' * 60)
        input('  Press ENTER here after you have logged in... ')

        # Navigate to Drive to verify
        driver.get('https://drive.google.com')
        time.sleep(PAGE_LOAD_WAIT)

        url = driver.current_url.lower()
        if 'accounts.google.com' in url or 'signin' in url:
            print('ERROR: Still not logged in. Please try again.')
            return False

    logger.info('Google login confirmed -- Drive is accessible')
    return True


# ============================================================================
# FILE UPLOAD VIA DRIVE WEB UI
# ============================================================================

def upload_to_drive(driver, files: list[Path], folder_name: str | None = None) -> bool:
    """Upload files to Google Drive via the web interface.

    Uses the hidden file input element that Drive creates for uploads.

    Args:
        driver: Selenium WebDriver.
        files: List of local file paths to upload.
        folder_name: If set, create/navigate to this folder first.

    Returns:
        True if upload was initiated successfully.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    # Navigate to Drive root
    driver.get('https://drive.google.com/drive/my-drive')
    time.sleep(PAGE_LOAD_WAIT)

    if folder_name:
        # Check if folder already exists by looking at folder links
        try:
            existing_folders = driver.find_elements(By.XPATH,
                f'//div[@data-tooltip="{folder_name}" and @role="gridcell"]'
                f'|//div[contains(@aria-label, "{folder_name}")]'
            )
            if existing_folders:
                # Double-click to open the folder
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).double_click(existing_folders[0]).perform()
                logger.info('Opened existing folder: %s', folder_name)
                time.sleep(PAGE_LOAD_WAIT)
            else:
                # Create the folder: use keyboard shortcut Shift+F
                # Actually, let's use the Drive API-like approach through the "New" button
                _create_drive_folder(driver, folder_name)
                time.sleep(PAGE_LOAD_WAIT)
        except Exception as e:
            logger.warning('Could not navigate to folder %s: %s, uploading to root', folder_name, e)

    # Upload files using Drive's file input
    # Google Drive has a hidden input[type=file] that we can use
    # If not present, we inject one
    upload_input = _get_or_create_upload_input(driver)
    if not upload_input:
        logger.error('Could not create upload input')
        return False

    # Send all file paths to the input
    file_paths = '\n'.join(str(f) for f in files)
    try:
        upload_input.send_keys(file_paths)
        logger.info('Sent %d files to upload input', len(files))

        # Wait for upload to process
        wait_time = max(UPLOAD_BATCH_WAIT, len(files) * UPLOAD_WAIT_PER_FILE)
        logger.info('Waiting %ds for upload to complete...', wait_time)
        time.sleep(wait_time)

        # Check for upload progress/completion indicators
        _wait_for_upload_complete(driver, timeout=max(120, len(files) * 10))
        return True

    except Exception as e:
        logger.error('Upload failed: %s', e)
        return False


def _get_or_create_upload_input(driver):
    """Find or create a file upload input element."""
    from selenium.webdriver.common.by import By

    # Look for existing file input
    inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
    for inp in inputs:
        try:
            if inp.is_enabled():
                return inp
        except Exception:
            continue

    # Inject a file input element
    try:
        driver.execute_script("""
            var input = document.createElement('input');
            input.type = 'file';
            input.id = '_luna_upload';
            input.multiple = true;
            input.style.position = 'fixed';
            input.style.top = '0';
            input.style.left = '0';
            input.style.opacity = '0.01';
            input.style.zIndex = '999999';
            document.body.appendChild(input);

            // When files are selected, trigger Drive's upload
            input.addEventListener('change', function() {
                var dt = new DataTransfer();
                for (var i = 0; i < input.files.length; i++) {
                    dt.items.add(input.files[i]);
                }
                // Dispatch a drop event on the Drive file list
                var target = document.querySelector('[role="main"]') || document.body;
                var dropEvent = new DragEvent('drop', {
                    dataTransfer: dt,
                    bubbles: true,
                    cancelable: true
                });
                target.dispatchEvent(dropEvent);
            });
        """)
        time.sleep(1)
        inp = driver.find_element(By.ID, '_luna_upload')
        return inp
    except Exception as e:
        logger.warning('Could not inject upload input: %s', e)
        return None


def _create_drive_folder(driver, folder_name: str) -> None:
    """Create a folder on Google Drive via the web UI."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        # Click "New" button
        new_buttons = driver.find_elements(By.XPATH,
            '//button[.//span[text()="New"]]'
            '|//div[contains(@class, "a-v-T") and contains(text(), "New")]'
            '|//button[contains(@aria-label, "New")]'
        )
        if new_buttons:
            new_buttons[0].click()
            time.sleep(2)

            # Click "New folder"
            folder_items = driver.find_elements(By.XPATH,
                '//div[contains(text(), "New folder")]'
                '|//span[contains(text(), "New folder")]'
                '|//div[contains(@class, "menuitem") and .//span[contains(text(), "folder")]]'
            )
            if folder_items:
                folder_items[0].click()
                time.sleep(2)

                # Type folder name in the dialog
                name_input = driver.find_element(By.XPATH,
                    '//input[contains(@class, "rename")]'
                    '|//input[@type="text" and @aria-label]'
                    '|//input[@type="text"]'
                )
                name_input.clear()
                name_input.send_keys(folder_name)
                time.sleep(1)

                # Click Create
                create_buttons = driver.find_elements(By.XPATH,
                    '//button[contains(text(), "Create")]'
                    '|//button[.//span[contains(text(), "Create")]]'
                )
                if create_buttons:
                    create_buttons[0].click()
                    logger.info('Created folder: %s', folder_name)
                    time.sleep(3)

                    # Double-click to enter the folder
                    driver.get('https://drive.google.com/drive/my-drive')
                    time.sleep(PAGE_LOAD_WAIT)
                    folders = driver.find_elements(By.XPATH,
                        f'//div[@data-tooltip="{folder_name}"]'
                    )
                    if folders:
                        ActionChains(driver).double_click(folders[0]).perform()
                        time.sleep(PAGE_LOAD_WAIT)
    except Exception as e:
        logger.warning('Could not create folder: %s', e)


def _wait_for_upload_complete(driver, timeout: int = 120) -> None:
    """Wait for Drive upload to complete by watching for progress indicators."""
    from selenium.webdriver.common.by import By

    start = time.time()
    last_log = 0
    while (time.time() - start) < timeout:
        try:
            # Check for upload progress bar or status text
            progress = driver.find_elements(By.XPATH,
                '//div[contains(@class, "upload")]'
                '|//div[contains(text(), "upload")]'
                '|//span[contains(text(), "Upload complete")]'
                '|//div[contains(@class, "progress")]'
            )
            for p in progress:
                text = p.text.lower()
                if 'complete' in text or 'done' in text:
                    logger.info('Upload complete')
                    return
        except Exception:
            pass

        if time.time() - last_log > 15:
            logger.info('Upload in progress... (%ds)', int(time.time() - start))
            last_log = time.time()

        time.sleep(3)

    logger.info('Upload wait timeout reached (%ds) - proceeding', timeout)


# ============================================================================
# ALTERNATIVE: MANUAL UPLOAD WITH SELENIUM-ASSISTED COLAB
# ============================================================================

def upload_via_drive_url(driver, files: list[Path]) -> bool:
    """Upload files one at a time using Drive's upload URL pattern.

    Falls back to opening the Drive upload dialog directly.

    Args:
        driver: Selenium WebDriver.
        files: List of local file paths.

    Returns:
        True if upload was initiated.
    """
    from selenium.webdriver.common.by import By

    driver.get('https://drive.google.com/drive/my-drive')
    time.sleep(PAGE_LOAD_WAIT)

    # Find the file input used by Drive's "File upload" button
    # Click New -> File upload to expose the input
    try:
        new_btn = driver.find_element(By.XPATH,
            '//button[.//span[text()="New"]]'
            '|//button[contains(@aria-label, "New")]'
        )
        new_btn.click()
        time.sleep(2)

        file_upload = driver.find_element(By.XPATH,
            '//div[contains(text(), "File upload")]'
            '|//span[contains(text(), "File upload")]'
        )
        file_upload.click()
        time.sleep(2)

        # Now there should be a file input dialog -- find the actual input element
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        if inputs:
            # Send file paths
            file_paths = '\n'.join(str(f) for f in files)
            inputs[-1].send_keys(file_paths)
            logger.info('Sent %d files to upload dialog', len(files))

            # Wait for completion
            _wait_for_upload_complete(driver, timeout=max(120, len(files) * 10))
            return True

    except Exception as e:
        logger.warning('Upload via menu failed: %s', e)

    return False


# ============================================================================
# COLAB NOTEBOOK LAUNCH
# ============================================================================

def find_notebook_on_drive(driver) -> str | None:
    """Find the notebook file on Google Drive and get its file ID.

    Returns:
        Google Drive file ID or None.
    """
    from selenium.webdriver.common.by import By

    driver.get('https://drive.google.com/drive/my-drive')
    time.sleep(PAGE_LOAD_WAIT)

    # Search for the notebook
    try:
        # Use Drive search
        search = driver.find_element(By.CSS_SELECTOR,
            'input[aria-label="Search in Drive"]'
            ',input[placeholder*="Search"]'
        )
        search.clear()
        search.send_keys('luna_avatar_generator.ipynb')
        time.sleep(1)
        from selenium.webdriver.common.keys import Keys
        search.send_keys(Keys.RETURN)
        time.sleep(PAGE_LOAD_WAIT)

        # Find the file in search results and get its URL
        file_elements = driver.find_elements(By.XPATH,
            '//div[contains(@data-tooltip, "luna_avatar_generator")]'
            '|//div[contains(@aria-label, "luna_avatar_generator")]'
        )
        if file_elements:
            # Right-click to get link, or just construct from data attributes
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).double_click(file_elements[0]).perform()
            time.sleep(5)

            # After double-clicking an ipynb, it may open in Colab
            url = driver.current_url
            if 'colab' in url and '/drive/' in url:
                # Extract file ID from URL
                parts = url.split('/drive/')
                if len(parts) > 1:
                    file_id = parts[1].split('?')[0].split('#')[0]
                    logger.info('Found notebook ID: %s', file_id)
                    return file_id

    except Exception as e:
        logger.warning('Search for notebook failed: %s', e)

    return None


def open_in_colab(driver, file_id: str | None = None) -> bool:
    """Open the notebook in Google Colab.

    Args:
        driver: Selenium WebDriver.
        file_id: Drive file ID. If None, search for it.

    Returns:
        True if notebook is loaded in Colab.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    if not file_id:
        file_id = find_notebook_on_drive(driver)

    if not file_id:
        logger.error('Could not find notebook on Drive')
        return False

    url = f'https://colab.research.google.com/drive/{file_id}'
    logger.info('Opening Colab: %s', url)
    driver.get(url)

    # Wait for Colab to fully load
    logger.info('Waiting for Colab to load (up to %ds)...', COLAB_FULL_LOAD_WAIT * 2)
    deadline = time.time() + COLAB_FULL_LOAD_WAIT * 2
    loaded = False
    while time.time() < deadline:
        try:
            # Check if notebook content is visible
            result = driver.execute_script("""
                return !!(
                    document.querySelector('colab-toolbar')
                    || document.querySelector('#toolbar')
                    || document.querySelector('.codecell-input-output')
                    || document.querySelector('.cell')
                    || document.querySelector('[class*="notebook"]')
                );
            """)
            if result:
                loaded = True
                break
        except Exception:
            pass
        time.sleep(3)

    if loaded:
        logger.info('Colab notebook loaded')
        time.sleep(5)  # Extra settle time
        return True
    else:
        logger.warning('Colab may not be fully loaded, proceeding anyway')
        return True  # Proceed optimistically


def set_t4_gpu(driver) -> None:
    """Try to set T4 GPU runtime."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    logger.info('Attempting to set T4 GPU runtime...')

    try:
        body = driver.find_element(By.TAG_NAME, 'body')

        # Try to open Runtime menu
        try:
            # Colab menus are often in a specific menubar
            menus = driver.find_elements(By.XPATH,
                '//span[text()="Runtime"]/..'
                '|//div[text()="Runtime"]'
            )
            for menu in menus:
                if menu.is_displayed():
                    menu.click()
                    time.sleep(2)

                    change_rt = driver.find_elements(By.XPATH,
                        '//span[text()="Change runtime type"]/..'
                        '|//div[contains(text(), "Change runtime type")]'
                    )
                    if change_rt:
                        change_rt[0].click()
                        time.sleep(3)

                        # In the dialog, find GPU selector
                        # Colab 2025+ uses a different dialog
                        # Try selecting T4 from any dropdown
                        selects = driver.find_elements(By.TAG_NAME, 'select')
                        for sel in selects:
                            options = sel.find_elements(By.TAG_NAME, 'option')
                            for opt in options:
                                if 'T4' in opt.text:
                                    opt.click()
                                    logger.info('Selected: %s', opt.text)
                                    break

                        # Also try mat-select / custom dropdowns
                        dropdowns = driver.find_elements(By.XPATH,
                            '//mat-select | //div[contains(@class, "select")]'
                        )
                        for dd in dropdowns:
                            try:
                                dd.click()
                                time.sleep(1)
                                t4_opts = driver.find_elements(By.XPATH,
                                    '//mat-option[contains(., "T4")]'
                                    '|//li[contains(., "T4")]'
                                    '|//div[@role="option" and contains(., "T4")]'
                                )
                                for opt in t4_opts:
                                    opt.click()
                                    logger.info('Selected T4 from dropdown')
                                    break
                            except Exception:
                                continue

                        # Click Save
                        time.sleep(1)
                        save_btns = driver.find_elements(By.XPATH,
                            '//button[contains(., "Save")]'
                            '|//button[contains(., "OK")]'
                        )
                        for btn in save_btns:
                            if btn.is_displayed():
                                btn.click()
                                logger.info('Saved runtime settings')
                                time.sleep(10)
                                break
                        else:
                            body.send_keys(Keys.ESCAPE)
                        break
            else:
                logger.info('Runtime menu not found - GPU may already be set or must be set manually')

        except Exception as e:
            logger.warning('GPU setup attempt: %s', e)
            try:
                body.send_keys(Keys.ESCAPE)
            except Exception:
                pass

    except Exception as e:
        logger.warning('GPU setup failed: %s (set manually if needed)', e)


def click_run_all(driver) -> bool:
    """Click Run All via Ctrl+F9."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    logger.info('Clicking Run All (Ctrl+F9)...')
    try:
        body = driver.find_element(By.TAG_NAME, 'body')
        body.send_keys(Keys.CONTROL + Keys.F9)
        time.sleep(3)

        # Handle any confirmation dialogs
        _handle_dialogs(driver)

        logger.info('Run All triggered')
        return True
    except Exception as e:
        logger.error('Run All failed: %s', e)
        return False


def _handle_dialogs(driver) -> None:
    """Click through any confirmation dialogs."""
    from selenium.webdriver.common.by import By

    time.sleep(2)
    try:
        buttons = driver.find_elements(By.XPATH,
            '//button[text()="OK"]'
            '|//button[text()="Yes"]'
            '|//button[text()="Run anyway"]'
            '|//button[contains(text(), "Run anyway")]'
            '|//paper-button[text()="OK"]'
        )
        for btn in buttons:
            if btn.is_displayed():
                btn.click()
                logger.info('Clicked dialog: %s', btn.text)
                time.sleep(1)
    except Exception:
        pass


def inject_keepalive(driver) -> None:
    """Inject keep-alive JavaScript into Colab page."""
    logger.info('Injecting keep-alive JavaScript...')
    try:
        driver.execute_script(KEEP_ALIVE_JS)
        logger.info('Keep-alive active')
    except Exception as e:
        logger.warning('Keep-alive injection failed: %s', e)


# ============================================================================
# PROGRESS MONITORING (via Colab page reading)
# ============================================================================

def monitor_progress(driver) -> None:
    """Monitor Colab execution by reading cell outputs."""
    from selenium.webdriver.common.by import By

    logger.info('Monitoring Colab execution...')
    print()
    print('=' * 60)
    print('  NOTEBOOK IS RUNNING')
    print('  Keep this window open! Monitoring progress...')
    print('  Press Ctrl+C to stop monitoring (notebook keeps running)')
    print('=' * 60)
    print()

    start = time.time()
    last_status = ''

    try:
        while True:
            elapsed = (time.time() - start) / 60
            try:
                # Read all cell output text
                outputs = driver.find_elements(By.CSS_SELECTOR,
                    '.output_text, .output_area pre, .rendered_html'
                )
                latest_text = ''
                for out in outputs[-5:]:  # Check last few cells
                    text = out.text.strip()
                    if text:
                        latest_text = text

                # Check for key status strings
                if 'BATCH COMPLETE' in latest_text or 'BATCH GENERATION COMPLETE' in latest_text:
                    print(f'\n[{elapsed:.0f}m] GENERATION COMPLETE!')
                    print('Images saved to Google Drive at /MyDrive/luna_avatars/')
                    return

                if 'Environment ready' in latest_text and 'MODEL_READY' not in last_status:
                    print(f'[{elapsed:.0f}m] Environment setup complete')

                if 'Pipeline ready' in latest_text and 'PIPELINE' not in last_status:
                    print(f'[{elapsed:.0f}m] Model loaded and quantized')
                    last_status = 'PIPELINE'

                # Look for generation progress
                for out in outputs:
                    text = out.text
                    if text and '/' in text and any(x in text for x in ['GENERATING', 'Prompt:', 'base:', 'Done in']):
                        # Extract latest progress line
                        lines = text.strip().split('\n')
                        for line in reversed(lines):
                            if '/' in line and ('[' in line or 'GENERATING' in line):
                                status = line.strip()[:100]
                                if status != last_status:
                                    print(f'[{elapsed:.0f}m] {status}')
                                    last_status = status
                                break

                # Check for errors
                for out in outputs:
                    text = out.text.lower()
                    if 'error' in text and 'no gpu' in text:
                        print(f'[{elapsed:.0f}m] ERROR: No GPU! Set Runtime > T4 GPU manually.')
                        return

            except Exception:
                pass  # Page may be temporarily unresponsive

            time.sleep(CELL_RUN_CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f'\n[{elapsed:.0f}m] Monitoring stopped. Notebook continues running in Firefox.')
        print('The keep-alive JS will keep the session active.')


# ============================================================================
# MAIN
# ============================================================================

def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description='Luna Avatar Generator - Zero-Setup Colab Launcher',
    )
    parser.add_argument('--run-only', action='store_true',
                        help='Skip upload (files already on Drive)')
    parser.add_argument('--notebook-id',
                        help='Drive file ID of notebook (skip search)')
    parser.add_argument('--debug', action='store_true',
                        help='Debug logging')
    return parser.parse_args()


def main() -> None:
    """Full automated pipeline."""
    args = parse_args()
    setup_logging(args.debug)

    print()
    print('=' * 60)
    print('  Luna Avatar Generator - Automated Colab Launcher')
    print('  4,870 images | Flux Kontext | Free T4 GPU')
    print('=' * 60)
    print()

    # Verify source files exist
    logger.info('Checking source files...')
    if not BASE_IMAGES_DIR.exists():
        print(f'ERROR: BASE_IMAGES not found at {BASE_IMAGES_DIR}')
        sys.exit(1)
    base_images = sorted(
        f for f in BASE_IMAGES_DIR.iterdir()
        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')
    )
    logger.info('  %d base images ready', len(base_images))

    if not MANIFEST_FILE.exists():
        print(f'ERROR: prompt_manifest.py not found at {MANIFEST_FILE}')
        sys.exit(1)
    logger.info('  prompt_manifest.py ready')

    if not NOTEBOOK_FILE.exists():
        print(f'ERROR: Notebook not found at {NOTEBOOK_FILE}')
        sys.exit(1)
    logger.info('  luna_avatar_generator.ipynb ready')

    # Launch Firefox
    logger.info('Starting Firefox...')
    driver = create_driver()

    try:
        # Step 1: Ensure Google login
        if not ensure_google_login(driver):
            print('Cannot proceed without Google login.')
            driver.quit()
            sys.exit(1)

        # Step 2: Upload files to Drive
        notebook_id = args.notebook_id
        if not args.run_only:
            print()
            logger.info('--- PHASE 1: Upload files to Google Drive ---')

            # Upload BASE_IMAGES to a folder
            logger.info('Uploading %d base images...', len(base_images))
            upload_to_drive(driver, base_images, folder_name='BASE_IMAGES')

            # Upload manifest and notebook to root
            logger.info('Uploading prompt_manifest.py and notebook...')
            upload_via_drive_url(driver, [MANIFEST_FILE, NOTEBOOK_FILE])

            logger.info('Upload phase complete')
        else:
            logger.info('Skipping upload (--run-only)')

        # Step 3: Open notebook in Colab
        print()
        logger.info('--- PHASE 2: Launch notebook in Colab ---')
        if not open_in_colab(driver, notebook_id):
            print('Could not open notebook in Colab.')
            print('Please ensure luna_avatar_generator.ipynb is on your Google Drive.')
            driver.quit()
            sys.exit(1)

        # Step 4: Set T4 GPU
        set_t4_gpu(driver)

        # Step 5: Handle any connect dialogs
        _handle_dialogs(driver)

        # Step 6: Click Run All
        if not click_run_all(driver):
            print('Failed to trigger Run All. Try manually: Ctrl+F9')

        # Step 7: Inject keep-alive
        time.sleep(5)
        inject_keepalive(driver)

        # Step 8: Monitor progress
        print()
        logger.info('--- PHASE 3: Monitor progress ---')
        monitor_progress(driver)

        # Done
        print()
        print('=' * 60)
        print('  LAUNCHER COMPLETE')
        print()
        print('  Results will be at: Google Drive > luna_avatars/')
        print('  Download later with: python colab/launch.py --download-only')
        print('=' * 60)

    except KeyboardInterrupt:
        print('\nLauncher interrupted. Firefox remains open.')
        print('The notebook will continue running in the browser.')

    except Exception as e:
        logger.error('Unexpected error: %s', e, exc_info=True)
        print(f'\nError: {e}')
        print('Firefox remains open -- you can continue manually.')

    # DON'T close the browser -- the notebook needs it running
    print('\nKeeping Firefox open (notebook needs it running).')
    print('Close Firefox manually when generation is done.')
    print('Or press Ctrl+C to exit this script (Firefox stays open).')

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print('\nExiting. Firefox stays open.')


if __name__ == '__main__':
    main()
