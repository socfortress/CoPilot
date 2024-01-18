from loguru import logger
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import json
from fastapi import HTTPException
from app.customer_provisioning.schema.graylog import StreamCreationResponse
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse

from app.integrations.office365.schema.provision import ProvisionOffice365Request
from app.customer_provisioning.schema.graylog import GraylogIndexSetCreationResponse
from app.integrations.office365.schema.provision import ProvisionOffice365Response, ProvisionOffice365AuthKeys, PipelineRuleTitles, CreatePipelineRule
from app.integrations.alert_escalation.services.general_alert import create_alert
from app.integrations.routes import get_customer_integrations_by_customer_code, find_customer_integration
from app.integrations.schema import CustomerIntegrationsResponse, CustomerIntegrations
from app.connectors.graylog.services.pipelines import get_pipelines
from app.connectors.graylog.utils.universal import send_delete_request
from app.connectors.graylog.utils.universal import send_post_request
from typing import Dict, List
from app.customer_provisioning.schema.graylog import Office365EventStream
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.customer_provisioning.schema.graylog import TimeBasedIndexSet
from app.customers.routes.customers import get_customer
from app.connectors.graylog.services.pipelines import get_pipeline_rules


############ ! WAZUH MANAGER ! ############
async def get_wazuh_configuration() -> str:
    """
    Retrieves the Wazuh configuration from the manager.

    Returns:
        str: The Wazuh configuration data.
    """
    endpoint = "manager/configuration"
    params = {"raw": True}
    response = await send_get_request(endpoint=endpoint, params=params)
    return response['data']

async def office365_template_with_api_type(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> str:
    """
    Returns a configured Office365 template for Wazuh.

    Args:
        wazuh_config (str): The current Wazuh configuration.
        tenant_id (str): Office365 Tenant ID.
        client_id (str): Office365 Client ID.
        client_secret (str): Office365 Client Secret.
        api_type (str): The type of Office365 API.

    Returns:
        str: The Office365 template configured with the given parameters.
    """

    template = f"""
    <ossec_config>
    <office365>
        <enabled>yes</enabled>
        <interval>1m</interval>
        <curl_max_size>5M</curl_max_size>
        <only_future_events>yes</only_future_events>
        <!-- Office365 Integration For {customer_code} -->
        <api_auth>
            <tenant_id>{provision_office365_auth_keys.TENANT_ID}</tenant_id>
            <client_id>{provision_office365_auth_keys.CLIENT_ID}</client_id>
            <client_secret>{provision_office365_auth_keys.CLIENT_SECRET}</client_secret>
            <api_type>{provision_office365_auth_keys.API_TYPE}</api_type>
        </api_auth>
        <subscriptions>
            <subscription>Audit.SharePoint</subscription>
            <subscription>Audit.Exchange</subscription>
            <subscription>DLP.ALL</subscription>
            <subscription>Audit.General</subscription>
            <subscription>Audit.AzureActiveDirectory</subscription>
        </subscriptions>
    </office365>
    </ossec_config>
    """

    return template

async def office365_template(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> str:
    """
    Returns a configured Office365 template for Wazuh.

    Args:
        wazuh_config (str): The current Wazuh configuration.
        tenant_id (str): Office365 Tenant ID.
        client_id (str): Office365 Client ID.
        client_secret (str): Office365 Client Secret.
        api_type (str): The type of Office365 API.

    Returns:
        str: The Office365 template configured with the given parameters.
    """

    template = f"""
    <ossec_config>
    <office365>
        <enabled>yes</enabled>
        <interval>1m</interval>
        <curl_max_size>5M</curl_max_size>
        <only_future_events>yes</only_future_events>
        <!-- Office365 Integration For {customer_code} -->
        <api_auth>
            <tenant_id>{provision_office365_auth_keys.TENANT_ID}</tenant_id>
            <client_id>{provision_office365_auth_keys.CLIENT_ID}</client_id>
            <client_secret>{provision_office365_auth_keys.CLIENT_SECRET}</client_secret>
        </api_auth>
        <subscriptions>
            <subscription>Audit.SharePoint</subscription>
            <subscription>Audit.Exchange</subscription>
            <subscription>DLP.ALL</subscription>
            <subscription>Audit.General</subscription>
            <subscription>Audit.AzureActiveDirectory</subscription>
        </subscriptions>
    </office365>
    </ossec_config>
    """

    return template

async def append_office365_template(wazuh_config: str, office365_template: str) -> str:
    """
    Appends the Office365 template to the Wazuh configuration.

    Args:
        wazuh_config (str): The current Wazuh configuration.
        office365_template (str): The Office365 template to append.

    Returns:
        str: The Wazuh configuration with the Office365 template appended.
    """

    return wazuh_config + office365_template

async def update_wazuh_configuration(wazuh_config: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> None:
    """
    Updates the Wazuh configuration. If it fails, remove the <api_type> tag and retry.

    Args:
        wazuh_config (str): The Wazuh configuration in string format.
        provision_office365_auth_keys (ProvisionOffice365AuthKeys): The Office365 authentication keys.
    """
    endpoint = "manager/configuration"
    data = wazuh_config.encode('utf-8')

    try:
        # First attempt to update configuration
        response = await send_put_request(endpoint=endpoint, data=data, binary_data=True)
        if response.get('success') and response['data'].get('error') == 0:
            logger.info("Wazuh configuration updated successfully.")
            return
        else:
            logger.error("Failed to update Wazuh configuration. Error: {}".format(response))

    except Exception as e:
        logger.error(f"Exception occurred during Wazuh configuration update: {e}")

    # Remove <api_type> tag and retry
    api_type_tag = f"<api_type>{provision_office365_auth_keys.API_TYPE}</api_type>"
    modified_wazuh_config = wazuh_config.replace(api_type_tag, "")
    data = modified_wazuh_config.encode('utf-8')

    try:
        response = await send_put_request(endpoint=endpoint, data=data, binary_data=True)
        if response.get('success') and response['data'].get('error') == 0:
            logger.info("Wazuh configuration updated successfully after removing <api_type> tag.")
        else:
            logger.error("Failed to update Wazuh configuration after removing <api_type> tag. Error: {}".format(response))

    except Exception as e:
        logger.error(f"Exception occurred during retry of Wazuh configuration update: {e}")
        raise HTTPException(status_code=500, detail="Failed to update Wazuh configuration.")


async def check_if_office365_is_already_provisioned(customer_code: str, wazuh_config: str) -> bool:
    """
    If the string "Office365 Integration For {customer_code}" is found in the Wazuh configuration, return True.

    Args:
        customer_code (str): The customer code.
        wazuh_config (str): The Wazuh configuration in string format.

    Returns:
        bool: True if the Office365 integration is already provisioned, False otherwise.
    """
    if f"Office365 Integration For {customer_code}" in wazuh_config:
        raise HTTPException(status_code=400, detail=f"Office365 integration already provisioned for customer {customer_code}.")


async def restart_wazuh_manager() -> None:
    """
    Restarts the Wazuh manager service.
    """
    logger.info("Restarting Wazuh manager service.")
    await send_put_request(endpoint="manager/restart", data=None)


################## ! GRAYLOG ! ##################

async def build_index_set_config(customer_code: str, session: AsyncSession) -> TimeBasedIndexSet:
    """
    Build the configuration for a time-based index set.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.

    Returns:
        TimeBasedIndexSet: The configured time-based index set.
    """
    return TimeBasedIndexSet(
        title=f"Office365 - {(await get_customer(customer_code, session)).customer.customer_name}",
        description=f"Office365 - {customer_code}",
        index_prefix=f"office365_{customer_code}",
        rotation_strategy_class="org.graylog2.indexer.rotation.strategies.TimeBasedRotationStrategy",
        rotation_strategy={
            "type": "org.graylog2.indexer.rotation.strategies.TimeBasedRotationStrategyConfig",
            "rotation_period": "P1D",
            "rotate_empty_index_set": False,
            "max_rotation_period": None,
        },
        retention_strategy_class="org.graylog2.indexer.retention.strategies.DeletionRetentionStrategy",
        retention_strategy={
            "type": "org.graylog2.indexer.retention.strategies.DeletionRetentionStrategyConfig",
            "max_number_of_indices": 30,
        },
        creation_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        index_analyzer="standard",
        shards=1,
        replicas=0,
        index_optimization_max_num_segments=1,
        index_optimization_disabled=False,
        writable=True,
        field_type_refresh_interval=5000,
    )

# Function to send the POST request and handle the response
async def send_index_set_creation_request(index_set: TimeBasedIndexSet) -> GraylogIndexSetCreationResponse:
    """
    Sends a request to create an index set in Graylog.

    Args:
        index_set (TimeBasedIndexSet): The index set to be created.

    Returns:
        GraylogIndexSetCreationResponse: The response from Graylog after creating the index set.
    """
    json_index_set = json.dumps(index_set.dict())
    logger.info(f"json_index_set set: {json_index_set}")
    response_json = await send_post_request(endpoint="/api/system/indices/index_sets", data=index_set.dict())
    return GraylogIndexSetCreationResponse(**response_json)


# Refactored create_index_set function
async def create_index_set(customer_code: str, session: AsyncSession) -> GraylogIndexSetCreationResponse:
    """
    Creates an index set for a new customer.

    Args:
        request (ProvisionNewCustomer): The request object containing the customer information.

    Returns:
        GraylogIndexSetCreationResponse: The response object containing the result of the index set creation.
    """
    logger.info(f"Creating index set for customer {customer_code}")
    index_set_config = await build_index_set_config(customer_code, session)
    return await send_index_set_creation_request(index_set_config)


# Function to extract index set ID
def extract_index_set_id(response: GraylogIndexSetCreationResponse) -> str:
    """
    Extracts the index set ID from the given GraylogIndexSetCreationResponse object.

    Args:
        response (GraylogIndexSetCreationResponse): The GraylogIndexSetCreationResponse object.

    Returns:
        str: The index set ID extracted from the response.
    """
    return response.data.id

# ! Event STREAMS ! #
# Function to create event stream configuration
async def build_event_stream_config(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys, index_set_id: str, session: AsyncSession) -> Office365EventStream:
    """
    Build the configuration for a Wazuh event stream.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.

    Returns:
        Office365EventStream: The configured Wazuh event stream.
    """
    return Office365EventStream(
        title=f"Office365 EVENTS - {(await get_customer(customer_code, session)).customer.customer_name}",
        description=f"Office365 EVENTS - {(await get_customer(customer_code, session)).customer.customer_name}",
        index_set_id=index_set_id,
        rules=[
            {
                "field": "rule_group1",
                "type": 1,
                "inverted": False,
                "value": "office365",
            },
            {
                "field": "data_office365_OrganizationId",
                "type": 1,
                "inverted": False,
                "value": f"{provision_office365_auth_keys.TENANT_ID}",
            }
        ],
        matching_type="AND",
        remove_matches_from_default_stream=True,
        content_pack=None,
    )


async def send_event_stream_creation_request(event_stream: Office365EventStream) -> StreamCreationResponse:
    """
    Sends a request to create an event stream.

    Args:
        event_stream (WazuhEventStream): The event stream to be created.

    Returns:
        StreamCreationResponse: The response containing the created event stream.
    """
    json_event_stream = json.dumps(event_stream.dict())
    logger.info(f"json_event_stream set: {json_event_stream}")
    response_json = await send_post_request(endpoint="/api/streams", data=event_stream.dict())
    return StreamCreationResponse(**response_json)


async def create_event_stream(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys, index_set_id: str, session: AsyncSession):
    """
    Creates an event stream for a customer.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.

    Returns:
        The result of the event stream creation request.
    """
    event_stream_config = await build_event_stream_config(customer_code, provision_office365_auth_keys, index_set_id, session)
    return await send_event_stream_creation_request(event_stream_config)


# ! PIPELINES AND RULES ! #
async def check_pipeline_rules() -> None:
    """
    Checks if the pipeline rules exist in Graylog. If they don't, create them.
    """
    pipeline_rules = await get_pipeline_rules()
    non_existing_rules = await pipeline_rules_exists(pipeline_rules)
    if non_existing_rules:
        logger.info(f"Creating pipeline rules: {non_existing_rules}")
        await create_pipeline_rules(non_existing_rules)

async def pipeline_rules_exists(pipeline_rules: PipelineRulesResponse) -> List[str]:
    """
    Checks if the pipeline rules exist in Graylog and returns a list of non-existing pipeline rules.
    """
    return [
        rule_title.value
        for rule_title in PipelineRuleTitles
        if not any(rule.title == rule_title.value for rule in pipeline_rules.pipeline_rules)
    ]

async def create_pipeline_rules(non_existing_rules: List[str]) -> None:
    """
    Creates the given pipeline rules.
    """
    rule_creators = {
        "Office365 Timestamp - UTC": create_office365_utc_rule,
        "WAZUH CREATE FIELD SYSLOG LEVEL - INFO": create_wazuh_info_rule,
        "WAZUH CREATE FIELD SYSLOG LEVEL - WARNING": create_wazuh_warning_rule,
        "WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE": create_wazuh_notice_rule,
        "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT": create_wazuh_alert_rule,
    }

    for rule_title in non_existing_rules:
        logger.info(f"Creating pipeline rule {rule_title}.")
        await rule_creators[rule_title](rule_title)

async def create_office365_utc_rule(rule_title: str) -> None:
    """
    Creates the 'Office365 Timestamp - UTC' pipeline rule.
    """
    rule_source = (
        f"rule \"{rule_title}\"\n"
        "when\n"
        "  has_field(\"data_office_365_CreationTime\")\n"
        "then\n"
        "  let creation_time = $message.data_office_365_CreationTime;\n"
        "  set_field(\"timestamp_utc\", creation_time);\n"
        "end"
    )
    await create_pipeline_rule(CreatePipelineRule(title=rule_title, description=rule_title, source=rule_source))

async def create_wazuh_info_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - INFO' pipeline rule.
    """
    rule_source = (
        f"rule \"{rule_title}\"\n"
        "when\n"
        "  to_long($message.rule_level) > 0 AND to_long($message.rule_level) < 4\n"
        "then\n"
        "  set_field(\"syslog_level\", \"INFO\");\n"
        "end"
    )
    await create_pipeline_rule(CreatePipelineRule(title=rule_title, description=rule_title, source=rule_source))

async def create_wazuh_warning_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - WARNING' pipeline rule.
    """
    rule_source = (
        f"rule \"{rule_title}\"\n"
        "when\n"
        "  to_long($message.rule_level) > 7 AND to_long($message.rule_level) < 12\n"
        "then\n"
        "  set_field(\"syslog_level\", \"WARNING\");\n"
        "end"
    )
    await create_pipeline_rule(CreatePipelineRule(title=rule_title, description=rule_title, source=rule_source))

async def create_wazuh_notice_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE' pipeline rule.
    """
    rule_source = (
        f"rule \"{rule_title}\"\n"
        "when\n"
        "  to_long($message.rule_level) > 3 AND to_long($message.rule_level) < 8\n"
        "then\n"
        "  set_field(\"syslog_level\", \"NOTICE\");\n"
        "end"
    )
    await create_pipeline_rule(CreatePipelineRule(title=rule_title, description=rule_title, source=rule_source))

async def create_wazuh_alert_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - ALERT' pipeline rule.
    """
    rule_source = (
        f"rule \"{rule_title}\"\n"
        "when\n"
        "  to_long($message.rule_level) > 11\n"
        "then\n"
        "  set_field(\"syslog_level\", \"ALERT\");\n"
        "end"
    )
    await create_pipeline_rule(CreatePipelineRule(title=rule_title, description=rule_title, source=rule_source))

async def create_pipeline_rule(rule: CreatePipelineRule) -> None:
    """
    Creates a pipeline rule with the given title.
    """
    endpoint = "/api/system/pipelines/rule"
    data = {
        "title": rule.title,
        "description": rule.description,
        "source": rule.source,
    }
    await send_post_request(endpoint=endpoint, data=data)



################## ! MAIN FUNCTION ! ##################

async def provision_office365(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys, session: AsyncSession) -> ProvisionOffice365Response:
    logger.info(f"Provisioning Office365 integration for customer {customer_code}.")

    await check_pipeline_rules()
    return None


    # Create Index Set
    index_set_id = (await create_index_set(customer_code=customer_code, session=session)).data.id
    logger.info(f"Index set: {index_set_id}")
    # Create event stream
    await create_event_stream(customer_code, provision_office365_auth_keys, index_set_id, session)


    # Get Wazuh configuration
    wazuh_config = await get_wazuh_configuration()

    # Check if Office365 is already provisioned
    await check_if_office365_is_already_provisioned(customer_code, wazuh_config)

    # Create Office365 template
    office365_templated = await office365_template_with_api_type(customer_code, provision_office365_auth_keys)

    # Append Office365 template to Wazuh configuration
    wazuh_config = await append_office365_template(wazuh_config, office365_templated)

    # Update Wazuh configuration
    await update_wazuh_configuration(wazuh_config, provision_office365_auth_keys)

    # Restart Wazuh manager
    await restart_wazuh_manager()


