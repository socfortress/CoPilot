from typing import Optional
from typing import Set

from app.integrations.alert_creation.general.schema.alert import ValidIocFields
from app.integrations.alert_creation.office365.schema.exchange import IrisAlertContext
from app.integrations.alert_creation.office365.schema.exchange import IrisAlertPayload
from app.integrations.alert_creation.office365.schema.exchange import IrisAsset
from app.integrations.alert_creation.office365.schema.exchange import IrisIoc
from app.integrations.alert_creation.office365.schema.exchange import Office365ExchangeAlertRequest
from app.integrations.alert_creation.office365.schema.exchange import Office365ExchangeAlertResponse
from app.integrations.utils.schema import ShufflePayload
from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_alert
from app.integrations.utils.alerts import send_to_shuffle
from app.integrations.utils.alerts import validate_ioc_type
from app.utils import get_customer_alert_settings
from loguru import logger


def valid_ioc_fields() -> Set[str]:
    """
    Getter for the set of valid IoC fields.
    Returns
    -------
    Set[str]
        The set of valid IoC fields.
    """
    return {field.value for field in ValidIocFields}


def construct_alert_source_link(alert_details: Office365ExchangeAlertRequest) -> str:
    """
    Construct the alert source link for the alert details.
    Parameters
    ----------
    alert_details: CreateAlertRequest
        The alert details.
    Returns
    -------
    str
        The alert source link.
    """
    return (
        f"{get_grafana_url_from_config().grafana_url}/explore?left=%5B%22now-6h%22,%22now%22,%22O365%22,%7B%22refId%22"
        ":%22A%22,%22query%22:%22data_office365_Id:%5C%22"
        f"{alert_details.data_office365_Id}%5C%22%22,%22alias%22"
        ":%22%22,%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:%7B%22limit%22:%22500%22"
        "%7D%7D%5D,%22bucketAggs%22:%5B%5D,%22timeField%22:%22timestamp%22%7D%5D"
    )


def build_ioc_payload(
    alert_details: Office365ExchangeAlertRequest,
) -> Optional[IrisIoc]:
    for field in valid_ioc_fields():
        if hasattr(alert_details, field):
            ioc_value = getattr(alert_details, field)
            ioc_type = validate_ioc_type(ioc_value=ioc_value)
            return IrisIoc(
                ioc_value=ioc_value,
                ioc_description="IoC found in alert",
                ioc_tlp_id=1,
                ioc_type_id=ioc_type,
            )
    return None


def build_asset_payload(alert_details: Office365ExchangeAlertRequest) -> IrisAsset:
    if alert_details.data_office365_UserId:
        return IrisAsset(
            asset_name=alert_details.data_office365_UserId,
            asset_ip="n/a",
            asset_description="Office365 User ID",
            asset_type_id=1,
        )
    return IrisAsset()


def build_alert_context_payload(
    alert_details: Office365ExchangeAlertRequest,
) -> IrisAlertContext:
    customer_info_obj = get_customer_codes_from_config_office365(
        alert_details.data_office365_OrganizationId,
    )
    logger.info(f"Customer info: {customer_info_obj}")

    customer_id_str = f"{customer_info_obj.iris_code}, {customer_info_obj.customer_name}, {customer_info_obj.iris_case_index}"
    return IrisAlertContext(
        customer_id_full=customer_id_str,
        customer_iris_id=customer_info_obj.iris_code,
        customer_name=customer_info_obj.customer_name,
        customer_cases_index=customer_info_obj.iris_case_index,
        alert_id=alert_details.id,
        alert_name=alert_details.rule_description,
        alert_level=alert_details.rule_level,
        rule_id=alert_details.rule_id,
        asset_name=alert_details.data_office365_UserId,
        asset_ip="n/a",
        asset_type=1,
        office365_operation=alert_details.data_office365_Operation,
        data_office365_Id=alert_details.data_office365_Id,
        rule_mitre_id=alert_details.rule_mitre_id,
        rule_mitre_technique=alert_details.rule_mitre_technique,
        rule_mitre_tactic=alert_details.rule_mitre_tactic,
    )


def build_alert_payload(
    alert_details: Office365ExchangeAlertRequest,
    ioc_payload: Optional[IrisIoc],
) -> IrisAlertPayload:
    asset_payload = build_asset_payload(alert_details)
    context_payload = build_alert_context_payload(alert_details)
    timefield = "timestamp_utc"
    # Get the timefield value from the alert_details
    if hasattr(alert_details, timefield):
        alert_details.time_field = getattr(alert_details, timefield)
    logger.info(f"Alert has context: {context_payload}")
    if ioc_payload:
        logger.info(f"Alert has IoC: {ioc_payload}")
        return IrisAlertPayload(
            alert_title=alert_details.data_office365_Operation,
            alert_source_link=construct_alert_source_link(alert_details),
            alert_description=alert_details.rule_description,
            alert_source="Office365 Exchange Rule",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=get_customer_codes_from_config_office365(
                alert_details.data_office365_OrganizationId,
            ).iris_code,
            alert_source_content=alert_details.to_dict(),
            alert_context=context_payload,
            alert_iocs=[ioc_payload],
            alert_source_event_time=alert_details.time_field,
        )
    else:
        logger.info("Alert does not have IoC")
        return IrisAlertPayload(
            alert_title=alert_details.data_office365_Operation,
            alert_source_link=construct_alert_source_link(alert_details),
            alert_description=alert_details.rule_description,
            alert_source="Office365 Exchange Rule",
            assets=[asset_payload],
            alert_status_id=3,
            alert_severity_id=5,
            alert_customer_id=get_customer_codes_from_config_office365(
                alert_details.data_office365_OrganizationId,
            ).iris_code,
            alert_source_content=alert_details.to_dict(),
            alert_context=context_payload,
            alert_source_event_time=alert_details.time_field,
        )


def create_exchange_alert(
    alert: Office365ExchangeAlertRequest,
) -> Office365ExchangeAlertResponse:
    logger.info(f"Creating Office365 Exchange alert {alert}) in IRIS.")
    ioc_payload = build_ioc_payload(alert_details=alert)
    iris_alert_payload = build_alert_payload(
        alert_details=alert,
        ioc_payload=ioc_payload,
    )
    client, alert_client = initialize_client_and_alert()
    result = fetch_and_validate_data(
        client,
        alert_client.add_alert,
        iris_alert_payload.to_dict(),
    )
    alert_id = result["data"]["alert_id"]
    send_to_shuffle(
        ShufflePayload(
            alert_id=alert_id,
            customer=get_customer_codes_from_config_office365(
                alert.data_office365_OrganizationId,
            ).customer_name,
            alert_source_link=construct_alert_source_link(alert),
            rule_description=alert.rule_description,
            hostname=alert.data_office365_UserId,
        ),
    )
    return Office365ExchangeAlertResponse(
        alert_id=alert_id,
        customer=get_customer_codes_from_config_office365(
            alert.data_office365_OrganizationId,
        ).customer_name,
        alert_source_link=construct_alert_source_link(alert),
        success=True,
        message=f"Successfully created alert {alert_id} in IRIS.",
    )
