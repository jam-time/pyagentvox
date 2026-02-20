"""Quick test: Dump Google Drive 'New' menu structure."""

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
import time

service = Service(GeckoDriverManager().install())
options = Options()
options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'
options.profile = r'C:\Users\jamea\AppData\Roaming\Mozilla\Firefox\Profiles\5m9eu33w.default-release'
options.add_argument('--width=1400')
options.add_argument('--height=1000')

driver = webdriver.Firefox(service=service, options=options)
driver.implicitly_wait(10)

driver.get('https://drive.google.com/drive/my-drive')
time.sleep(10)
print(f'On Drive: {driver.title}')

# Click New
driver.execute_script(
    "var btns = document.querySelectorAll('button');"
    "for (var i = 0; i < btns.length; i++) {"
    "  if (btns[i].textContent.trim() === 'New') { btns[i].click(); break; }"
    "}"
)
time.sleep(3)

# Dump all visible menu items
items = driver.find_elements(By.XPATH, '//*[@role="menuitem"]')
print(f'Total menuitems: {len(items)}')
for i, item in enumerate(items):
    try:
        visible = item.is_displayed()
        text = item.get_attribute('textContent').strip().replace('\n', ' | ')[:80]
        data_id = item.get_attribute('data-id') or ''
        aria = item.get_attribute('aria-label') or ''
        cls = item.get_attribute('class')[:60] if item.get_attribute('class') else ''
        print(f'  [{i}] visible={visible} text="{text}" data-id="{data_id}" aria="{aria}" class="{cls}"')
    except Exception as e:
        print(f'  [{i}] error: {e}')

# Also check for any elements with upload-related text
print()
print('Elements containing "upload":')
upload_els = driver.find_elements(By.XPATH, '//*[contains(text(), "upload") or contains(text(), "Upload")]')
for el in upload_els[:10]:
    try:
        tag = el.tag_name
        text = el.text.strip()[:60]
        cls = el.get_attribute('class')[:40] if el.get_attribute('class') else ''
        visible = el.is_displayed()
        print(f'  <{tag}> visible={visible} text="{text}" class="{cls}"')
    except Exception:
        pass

driver.quit()
print('Done')
