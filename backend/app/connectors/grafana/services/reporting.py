from typing import List

from fastapi import HTTPException
from loguru import logger
from playwright.async_api import async_playwright
from loguru import logger
import base64
import time
from datetime import datetime
from datetime import timedelta
from app.connectors.grafana.schema.reporting import TimeRange
import os
import sys
import subprocess
import pdfkit
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.grafana.schema.reporting import GenerateReportCreation, GenerateReportResponse, Base64Image, GenerateReportRequest, RequestPanel
from app.utils import get_connector_attribute
from app.connectors.grafana.schema.reporting import GrafanaGenerateIframeLinksRequest
from app.connectors.grafana.schema.reporting import GrafanaGenerateIframeLinksResponse
from app.connectors.grafana.schema.reporting import GrafanaLinksList

from app.connectors.grafana.schema.reporting import GrafanaDashboardDetails
from app.connectors.grafana.schema.reporting import GrafanaOrganizationDashboards
from app.connectors.grafana.schema.reporting import GrafanaOrganizations
from app.connectors.grafana.utils.universal import create_grafana_client
from pathlib import Path
from app.connectors.models import Connectors

async def get_grafana_url(session: AsyncSession):
    connector = await session.execute(select(Connectors).where(Connectors.connector_name == "Grafana"))
    connector = connector.scalars().first()
    return connector.connector_url

def calculate_unix_timestamps(time_range: TimeRange):
    now = datetime.now()
    if time_range.unit == "m":
        start_time = now - timedelta(minutes=time_range.value)
    elif time_range.unit == "h":
        start_time = now - timedelta(hours=time_range.value)
    elif time_range.unit == "d":
        start_time = now - timedelta(days=time_range.value)

    timestamp_from = int(time.mktime(start_time.timetuple())) * 1000
    timestamp_to = int(time.mktime(now.timetuple())) * 1000

    return timestamp_from, timestamp_to

def generate_panel_urls(grafana_url: str, request: GrafanaGenerateIframeLinksRequest, timestamp_from: int, timestamp_to: int):
    panel_links: List[GrafanaLinksList] = []
    #for panel_id in request.panel_ids:
    panel_url = (
        f"{grafana_url}/d-solo/{request.dashboard_uid}/{request.dashboard_title}"
        f"?orgId={request.org_id}&from={timestamp_from}&to={timestamp_to}"
        f"&panelId={request.panel_id}"
    )
    panel_links.append(GrafanaLinksList(panel_id=request.panel_id, panel_url=panel_url))
    return panel_links


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

async def capture_screenshots(page, panels: List[RequestPanel]) -> List[RequestPanel]:
    logger.info("Capturing screenshots")
    last_url = ""
    for panel in panels:
        try:
            # Check if the panel's URL is different from the last to optimize navigation
            if panel.panel_url != last_url:
                await page.goto(panel.panel_url)
                await page.wait_for_load_state(state='networkidle')
                last_url = panel.panel_url

            # Assuming default dimensions are always used in this example
            width = 910
            height = 683
            await page.set_viewport_size({"width": width, "height": height})

            screenshot = await page.screenshot(type='png')
            base64_image = base64.b64encode(screenshot).decode('utf-8')
            panel.panel_base64 = base64_image
        except Exception as e:
            print(f"Failed to capture screenshot for panel {panel.panel_id}: {e}")
            # Optionally, set panel_base64 to None or a default value in case of failure
            panel.panel_base64 = None
    return panels

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
    wkhtmltopdf_path = get_wkhtmltopdf_path()
    if wkhtmltopdf_path is None:
        logger.error("Cannot create PDF without wkhtmltopdf")
        return
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    pdfkit.from_string(html_string, 'report.pdf', configuration=config)


async def generate_grafana_iframe_links(
    request: GrafanaGenerateIframeLinksRequest,
    session: AsyncSession
):
    """
    Function to generate Grafana dashboard iframe links.

    Args:
        request (GrafanaGenerateIframeLinksRequest): The request body containing the dashboard UID and organization ID.

    Returns:
        GrafanaDashboardPanelsResponse: The response containing the result of the dashboard provisioning.
    """
    # get the Grafana URL from the database
    grafana_url = await get_grafana_url(session)
    logger.info(f"Grafana URL: {grafana_url}")

    # calculate the Unix timestamps based on the current time and the provided time range
    timestamp_from, timestamp_to = calculate_unix_timestamps(request.time_range)

    # build the URL string for each panel_id
    panel_urls = generate_panel_urls(grafana_url, request, timestamp_from, timestamp_to)

    # return only the panel url
    return panel_urls[0].panel_url



def generate_html(panels: List[RequestPanel]) -> str:
    # Load the template
    logger.info(f"Rendering HTML with panels: {len(panels)} panels")
    templates_dir = Path(__file__).parent / '../reporting'
    env = Environment(loader=FileSystemLoader(templates_dir))
    logger.info(f"Templates dir: {templates_dir}")
    template = env.get_template('report-template-test-new.html')

    panel_groups = {}
    for panel in panels:
        if panel.row_id not in panel_groups:
            panel_groups[panel.row_id] = [panel]
        else:
            panel_groups[panel.row_id].append(panel)

    # Convert the dict to a list of panel groups for the template
    panel_groups_list = list(panel_groups.values())

    # Render the template with the grouped panels
    html_content = template.render(panel_groups=panel_groups_list)
    return html_content

def parse_timerange(timerange: str) -> dict:
    """Parse the timerange string into a dictionary with value and unit keys."""
    timerange_value, timerange_unit = int(timerange[:-1]), timerange[-1]
    return {"value": timerange_value, "unit": timerange_unit}

async def generate_panel_urls_object(panel: RequestPanel, timerange: dict, session: AsyncSession) -> str:
    """Generate the iframe links for a panel."""
    iframe_links_request = GrafanaGenerateIframeLinksRequest(
        time_range=timerange,
        dashboard_uid=panel.dashboard_uid,
        dashboard_title=panel.dashboard_title,
        org_id=panel.org_id,
        panel_id=panel.panel_id
    )
    return await generate_grafana_iframe_links(iframe_links_request, session)

async def generate_report(
    request: GenerateReportRequest,
    session: AsyncSession
):
    logger.info("Generating report")
    logger.info(f"Request: {request}")
    for row in request.rows:
        for panel in row.panels:
            panel.row_id = row.id
    # Parse the timerange string
    timerange = parse_timerange(request.timerange)
    # Iterate over each row in the request
    for row in request.rows:
        # Iterate over each panel in the row
        for panel in row.panels:
            # Generate the iframe links for each panel
            panel_urls = await generate_panel_urls_object(panel, timerange, session)
            logger.info(f"Panel URLs: {panel_urls}")
            # add the panel url to the request.panel_url
            panel.panel_url = panel_urls

    logger.info(f"Request: {request}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        await login_to_page(page, session)
        if not await check_login_success(page):
            await browser.close()
            return
        # Flatten the list of panels
        all_panels = [panel for row in request.rows for panel in row.panels]
        panels = await capture_screenshots(page, all_panels)
        await browser.close()
        html_string = generate_html(panels)
        create_pdf(html_string)
        return GenerateReportResponse(
            message="Report generated successfully",
            success=True
        )
