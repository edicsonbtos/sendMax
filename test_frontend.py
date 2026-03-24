import sys
from playwright.sync_api import sync_playwright

def test_login(page):
    page.goto("http://localhost:3000/login")
    page.evaluate("() => { localStorage.setItem('token', 'fake_token'); document.cookie = 'auth_token=fake_token; path=/; max-age=86400'; }")
    page.goto("http://localhost:3000/ordenes/nueva")
    page.wait_for_timeout(2000)

    # Fill step 1
    page.fill('input[placeholder="Buscar por nombre o DNI..."]', 'John')
    page.wait_for_timeout(1000)

    # Try next
    page.click('text="Siguiente Paso"')
    page.wait_for_timeout(1000)

    # Screen step 2
    page.screenshot(path="orden_nueva_step2.png", full_page=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        test_login(page)
        print("Success")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
