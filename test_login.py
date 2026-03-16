import subprocess
import time

from playwright.sync_api import Page, expect, sync_playwright

def test_login(page: Page):
    print("Navigating to login page...")
    page.goto("http://localhost:3000/login")

    print("Waiting for page load...")
    page.wait_for_selector("form")

    print("Taking screenshot...")
    page.screenshot(path="/home/jules/verification/login_page.png")
    print("Screenshot saved to /home/jules/verification/login_page.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            test_login(page)
        finally:
            context.close()
            browser.close()
