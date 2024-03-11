from typing import List

from fastapi import HTTPException
from loguru import logger
from playwright.async_api import async_playwright
from loguru import logger
import base64
import os
import sys
import subprocess
import pdfkit
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession
from app.connectors.grafana.schema.reporting import GenerateReportRequest, GenerateReportResponse, Base64Image
from app.utils import get_connector_attribute

from app.connectors.grafana.schema.reporting import GrafanaDashboardDetails
from app.connectors.grafana.schema.reporting import GrafanaOrganizationDashboards
from app.connectors.grafana.schema.reporting import GrafanaOrganizations
from app.connectors.grafana.utils.universal import create_grafana_client
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.units import inch
from pathlib import Path


async def get_orgs() -> List[GrafanaOrganizations]:
    """
    Update a dashboard in Grafana.

    Args:
        dashboard_json (dict): The updated dashboard JSON.
        organization_id (int): The ID of the organization.
        folder_id (int): The ID of the folder.

    Returns:
        dict: The updated dashboard response.

    Raises:
        HTTPException: If there is an error updating the dashboard.
    """
    logger.info("Getting organizations from Grafana")
    try:
        grafana_client = await create_grafana_client("Grafana")
        orgs = grafana_client.organizations.list_organization()
        return orgs
    except Exception as e:
        logger.error(f"Failed to collect organizations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect organizations: {e}")


async def get_dashboards(org_id: int) -> List[GrafanaOrganizationDashboards]:
    """
    Get dashboards from Grafana.

    Returns:
        dict: The response containing the dashboards collected from Grafana.
    """
    logger.info("Getting dashboards from Grafana")
    try:
        grafana_client = await create_grafana_client("Grafana")
        logger.info(f"Switching to organization {org_id}")
        grafana_client.user.switch_actual_user_organisation(org_id)
        dashboards = grafana_client.search.search_dashboards()
        return dashboards
    except Exception as e:
        logger.error(f"Failed to collect dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect dashboards: {e}")


async def get_dashboard_details(dashboard_uid: str) -> GrafanaDashboardDetails:
    """
    Get dashboard details from Grafana.

    Args:
        dashboard_uid (str): The UID of the dashboard.

    Returns:
        dict: The response containing the dashboard details collected from Grafana.
    """
    logger.info("Getting dashboard details from Grafana")
    try:
        grafana_client = await create_grafana_client("Grafana")
        dashboard_details = grafana_client.dashboard.get_dashboard(dashboard_uid)
        return dashboard_details
    except Exception as e:
        logger.error(f"Failed to collect dashboard details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect dashboard details: {e}")

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

async def capture_screenshots(page, panels):
    base64_images = []
    for i, panel in enumerate(panels):
        await page.goto(panel.url)
        await page.wait_for_load_state(state='networkidle')
        await page.set_viewport_size({"width": panel.width, "height": panel.height})
        screenshot = await page.screenshot(type='png')
        base64_image = base64.b64encode(screenshot).decode('utf-8')
        base64_images.append({
            'url': panel.url,
            'base64_image': base64_image,
            'width': panel.width,
            'height': panel.height,
            'page_number': panel.page_number
        })
    base64_images.sort(key=lambda x: x['page_number'])
    return base64_images

def get_wkhtmltopdf_path():
    if sys.platform == 'win32':
        return 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
    elif sys.platform == 'darwin':
        return '/usr/local/bin/wkhtmltopdf'
    else:
        try:
            # Try to find the path using 'which' command in Linux
            path = subprocess.check_output(['which', 'wkhtmltopdf'])
            return path.strip()
        except Exception as e:
            logger.error(f"Could not find wkhtmltopdf: {e}")
            return None

def create_pdf(html_string):
    logger.info(f"Creating PDF from HTML: {html_string}")
    wkhtmltopdf_path = get_wkhtmltopdf_path()
    if wkhtmltopdf_path is None:
        logger.error("Cannot create PDF without wkhtmltopdf")
        return
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    pdfkit.from_string(html_string, 'report.pdf', configuration=config)


def generate_html(base64_images):
    # Load the template
    templates_dir = Path(__file__).parent / '../reporting'
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('report-template-test.html')

    # Define the context
    context = {
        'panels': base64_images,  # Assuming this is adjusted to contain base64 encoded images
    }

    # Render the template with the context
    html_string = template.render(context)

    return html_string

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
        base64_images = await capture_screenshots(page, request.panels)
        await browser.close()
        html_string = generate_html(base64_images)
        create_pdf(html_string)
        return GenerateReportResponse(
            base64_images=[Base64Image(url=img['url'], base64_image=img['base64_image']) for img in base64_images],
            message="Report generated successfully",
            success=True
        )
