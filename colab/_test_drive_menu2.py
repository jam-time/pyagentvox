"""Test: Dump Google Drive 'New' menu using class-based selectors."""

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

# Click New button
driver.execute_script(
    "var btns = document.querySelectorAll('button');"
    "for (var i = 0; i < btns.length; i++) {"
    "  if (btns[i].textContent.trim() === 'New') { btns[i].click(); break; }"
    "}"
)
time.sleep(3)

# Dump ALL visible clickable elements
items = driver.execute_script("""
    var result = [];
    var all = document.querySelectorAll('div, span, a, li');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        if (el.offsetParent === null) continue;
        var text = (el.textContent || '').trim();
        if (!text || text.length > 60) continue;
        // Skip if nested inside another text element
        if (el.children.length > 3) continue;
        var rect = el.getBoundingClientRect();
        if (rect.width < 20 || rect.height < 15) continue;
        // Check if it looks like a menu item (has reasonable position)
        if (rect.left < 5 || rect.left > 500) continue;
        if (rect.top < 50 || rect.top > 800) continue;
        result.push({
            tag: el.tagName,
            text: text.substring(0, 60),
            x: Math.round(rect.left),
            y: Math.round(rect.top),
            w: Math.round(rect.width),
            h: Math.round(rect.height),
            cls: (el.className || '').substring(0, 40),
            id: el.id || ''
        });
    }
    // Sort by y position
    result.sort(function(a, b) { return a.y - b.y; });
    return result;
""")

print(f'Visible elements near menu area: {len(items)}')
seen_texts = set()
for item in items:
    text = item['text']
    key = f"{text}_{item['y']}"
    if key in seen_texts:
        continue
    seen_texts.add(key)
    if any(kw in text.lower() for kw in ['upload', 'folder', 'new', 'google', 'doc', 'sheet', 'slide', 'form', 'more']):
        print(f'  [{item["x"]},{item["y"]}] {item["w"]}x{item["h"]} <{item["tag"]}> "{text}" id={item["id"]} cls={item["cls"]}')

driver.quit()
print('Done')
