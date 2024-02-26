import base64
from typing import List

import httpx
from loguru import logger

from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.integrations.huntress.schema.huntress import CollectHuntressRequest
from app.integrations.huntress.schema.huntress import HuntressIncidentResponse
from app.integrations.huntress.schema.huntress import IncidentReport
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload


async def base64_encode(payload: CollectHuntressRequest) -> str:
    """Base64 encode the payload."""
    payload = f"{payload.apiKey}:{payload.secretKey}"
    payload_bytes = payload.encode("utf-8")
    base64_bytes = base64.b64encode(payload_bytes)
    base64_string = base64_bytes.decode("utf-8")
    return base64_string


async def make_request(url: str, auth: str) -> HuntressIncidentResponse:
    headers = {"Accept": "application/json", "Authorization": f"Basic {auth}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    return HuntressIncidentResponse(**response.json())


async def get_next_page(response: HuntressIncidentResponse) -> str:
    if response.pagination and response.pagination.next_page_url:
        return response.pagination.next_page_url
    return None


async def check_if_incident_exists(incident: IncidentReport) -> bool:
    """Check if the incident exists in the Wazuh-Indexer."""
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    results = es_client.search(
        index="huntress*",
        body={
            "size": 1000,
            "query": {"bool": {"must": [{"term": {"id": incident.id}}]}},
        },
    )
    if results["hits"]["total"]["value"] > 0:
        logger.info("Event already exists in Wazuh-Indexer...Skipping")
        return True
    return False


async def send_to_event_shipper(incident: IncidentReport, customer_code: str) -> None:
    exists = await check_if_incident_exists(incident)
    if not exists:
        message = EventShipperPayload(
            customer_code=customer_code,
            integration="huntress",
            version="1.0",
            **incident.to_dict(),
        )
        await event_shipper(message)
    return None


async def process_incidents(incidents: List[IncidentReport], customer_code: str) -> None:
    """Process a list of incidents."""
    for incident in incidents:
        await send_to_event_shipper(incident, customer_code)


async def process_pages(url: str, auth: str, customer_code: str) -> None:
    """Process all pages of incidents."""
    while url is not None:
        response = await make_request(url, auth)
        await process_incidents(response.incident_reports, customer_code)
        url = await get_next_page(response)


async def collect_huntress(request: CollectHuntressRequest) -> None:
    """Pull down Huntress Events."""
    logger.info(f"Collecting Huntress Events with request: {request}")
    base64_string = await base64_encode(request)
    logger.info(f"Base64 encoded string: {base64_string}")
    url = "https://api.huntress.io/v1/incident_reports?page=1&limit=100"
    await process_pages(url, base64_string, request.customer_code)
