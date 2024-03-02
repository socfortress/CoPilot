import asyncio
from playwright.async_api import async_playwright
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.reporting.schema.reporting import GenerateReportRequest
from app.utils import get_connector_attribute


async def login_to_page(page, session: AsyncSession):
    # Navigate to the login page
    await page.goto(f'{await get_connector_attribute(connector_id=12, column_name="connector_url", session=session)}/login')
    # Enter the username and password
    await page.fill('input[name="user"]', f'{await get_connector_attribute(connector_id=12, column_name="connector_username", session=session)}')
    await page.fill('input[name="password"]', f'{await get_connector_attribute(connector_id=12, column_name="connector_password", session=session)}')
    # Click the login button
    await page.click('button[data-testid="data-testid Login button"]')
    # Wait for navigation to complete
    await page.wait_for_load_state(state='networkidle')

async def check_login_success(page):
    # Check if login was successful by checking for an element that is only visible when logged in
    body_class = await page.evaluate('document.body.className')
    if 'app-grafana no-overlay-scrollbar page-dashboard' in body_class:
        print("Login successful")
        return True
    else:
        print("Login failed")
        return False

async def capture_screenshots(page, urls):
    for url in urls:
        await page.goto(url)
        await page.wait_for_load_state(state='networkidle')
        await page.screenshot(path=f'example-chromium-{urls.index(url)}.png')

async def generate_report(
    request: GenerateReportRequest,
    session: AsyncSession
):
    logger.info("Generating report")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        await login_to_page(page, session)
        if not await check_login_success(page):
            await browser.close()
            return
        await capture_screenshots(page, request.urls)
        await browser.close()

