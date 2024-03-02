import asyncio
from playwright.async_api import async_playwright
from loguru import logger


async def generate_report():
    logger.info("Generating report")
    async with async_playwright() as p:
        urls = [
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/huntress-summary?orgId=1&from=1708725633941&to=1709330433941&panelId=5',
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/huntress-summary?orgId=1&from=1708725654862&to=1709330454862&panelId=1',
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/a1891b09-fba9-498e-807e-1ad774c8557f/sap-users-auth?orgId=44&from=1709303384274&to=1709389784274&panelId=43',
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/huntress-summary?orgId=1&from=1706799780600&to=1709391780600&panelId=10'
            # Add more URLs here
        ]
        for browser_type in [p.chromium]:
            browser = await browser_type.launch(headless=False)
            page = await browser.new_page()
            # Navigate to the login page
            await page.goto('http://ashdevcopilot01.socfortress.local:3000/login')
            # Enter the username and password
            await page.fill('input[name="user"]', 'admin')
            await page.fill('input[name="password"]', 'socfortress')
            # Click the login button
            await page.click('button[data-testid="data-testid Login button"]')
            # Wait for navigation to complete
            await page.wait_for_load_state(state='networkidle')
            # Check if login was successful by checking for an element that is only visible when logged in
            body_class = await page.evaluate('document.body.className')
            if 'app-grafana no-overlay-scrollbar page-dashboard' in body_class:
                print("Login successful")
            else:
                print("Login failed")
                await browser.close()
                return
            for url in urls:
                await page.goto(url)
                #await asyncio.sleep(15)
                await page.wait_for_load_state(state='networkidle')
                await page.screenshot(path=f'example-{browser_type.name}-{urls.index(url)}.png')
            await browser.close()

