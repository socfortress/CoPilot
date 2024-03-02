import asyncio
from playwright.async_api import async_playwright
from loguru import logger
import base64
from sqlalchemy.ext.asyncio import AsyncSession
from app.reporting.schema.reporting import GenerateReportRequest, GenerateReportResponse, Base64Image
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
    base64_images = []
    for url in urls:
        await page.goto(url)
        await page.wait_for_load_state(state='networkidle')
        screenshot = await page.screenshot(type='png')
        base64_image = base64.b64encode(screenshot).decode('utf-8')
        base64_images.append({"url": url, "base64_image": base64_image})
    return base64_images

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
        base64_images = await capture_screenshots(page, request.urls)
        await browser.close()
        return GenerateReportResponse(
            base64_images=[Base64Image(url=img['url'], base64_image=img['base64_image']) for img in base64_images],
            message="Report generated successfully",
            success=True
        )
