import requests
from loguru import logger

from app.integrations.sap_siem.schema.sap_siem import CollectSapSiemRequest
from app.integrations.sap_siem.schema.sap_siem import InvokeSAPSiemResponse
from app.integrations.sap_siem.schema.sap_siem import SapSiemResponseBody
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload


def build_request_payload(sap_siem_request: CollectSapSiemRequest) -> dict:
    return {
        "apiKey": sap_siem_request.apiKey,
        "secret": sap_siem_request.secretKey,
        "userKey": sap_siem_request.userKey,
        "query": f"SELECT * FROM auditLog WHERE endpoint = 'accounts.login' and @timestamp >= '{sap_siem_request.lower_bound}' "
        f"and @timestamp < '{sap_siem_request.upper_bound}'",
    }


async def make_request(sap_siem_request: CollectSapSiemRequest) -> SapSiemResponseBody:
    """
    Makes a request to the SAP SIEM integration.

    Args:
        sap_siem_request (CollectSapSiemRequest): The request payload containing the necessary information for the SAP SIEM integration.

    Returns:
        SapSiemResponseBody: The response model containing the result of the SAP SIEM integration invocation.

    Raises:
        HTTPException: If the SAP SIEM integration fails.
    """
    logger.info("Making request to SAP SIEM")
    form_data = build_request_payload(sap_siem_request)
    response = requests.post(
        f"https://{sap_siem_request.apiDomain}/audit.search",
        data=form_data,
    )
    return SapSiemResponseBody(**response.json())


async def send_to_event_shipper(message: EventShipperPayload) -> None:
    """
    Sends the message to the event shipper.

    Args:
        message (EventShipperPayload): The message to send to the event shipper.
    """
    await event_shipper(message)


async def collect_sap_siem(sap_siem_request: CollectSapSiemRequest) -> InvokeSAPSiemResponse:
    """
    Collects SAP SIEM events.

    Args:
        sap_siem_request (CollectSapSiemRequest): The request payload containing the necessary information for the SAP SIEM integration.

    Returns:
        InvokeSAPSiemResponse: The response model containing the result of the SAP SIEM integration invocation.

    Raises:
        HTTPException: If the SAP SIEM integration fails.
    """
    logger.info(f"Collecting SAP SIEM Events for customer_code: {sap_siem_request.customer_code}")

    results = await make_request(sap_siem_request)

    for result in results.results:
        # write the `timestamp` field as `event_timestamp`
        result.event_timestamp = result.timestamp
        await send_to_event_shipper(
            EventShipperPayload(
                customer_code=sap_siem_request.customer_code,
                integration="sap_siem",
                version="1.0",
                **result.dict(),
            ),
        )

    return InvokeSAPSiemResponse(
        success=True,
        message="SAP SIEM Events collected successfully",
    )
