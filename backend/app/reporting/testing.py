import asyncio
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from app.middleware.license import verify_license_key
from app.db.db_session import get_db
from sqlalchemy.ext.asyncio import AsyncSession


reporting_router = APIRouter()

@reporting_router.post(
    "/generate_report",
    description="Generate a report",
)
async def main(session: AsyncSession = Depends(get_db)):
    await verify_license_key(session)
    # async with async_playwright() as p:
    #     for browser_type in [p.chromium, p.firefox, p.webkit]:
    #         browser = await browser_type.launch()
    #         page = await browser.new_page()
    #         await page.goto('http://playwright.dev')
    #         await page.screenshot(path=f'example-{browser_type.name}.png')
    #         await browser.close()
    return {"message": "Report generated"}
