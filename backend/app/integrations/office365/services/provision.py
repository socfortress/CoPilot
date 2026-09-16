import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List
from typing import Optional
from urllib.parse import quote
from xml.dom import minidom
from xml.dom.minidom import parseString
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import parse
from xml.etree.ElementTree import tostring

import aiofiles
from dotenv import load_dotenv
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.schema.dashboards import Office365Dashboard
from app.connectors.grafana.services.dashboards import provision_dashboards
from app.connectors.grafana.services.folders import delete_folder
from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.graylog.schema.pipelines import CreatePipeline
from app.connectors.graylog.schema.pipelines import CreatePipelineRule
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.services.management import delete_index_by_id
from app.connectors.graylog.services.management import start_stream
from app.connectors.graylog.services.pipelines import connect_stream_to_pipeline
from app.connectors.graylog.services.pipelines import create_pipeline_graylog
from app.connectors.graylog.services.pipelines import create_pipeline_rule
from app.connectors.graylog.services.pipelines import get_pipeline_id
from app.connectors.graylog.services.pipelines import get_pipeline_rules
from app.connectors.graylog.services.pipelines import get_pipelines
from app.connectors.graylog.services.streams import delete_stream
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_post_request_create_entity
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.customer_provisioning.schema.grafana import GrafanaDatasource
from app.customer_provisioning.schema.grafana import GrafanaDataSourceCreationResponse
from app.customer_provisioning.schema.graylog import GraylogIndexSetCreationResponse
from app.customer_provisioning.schema.graylog import Office365EventStream
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.customer_provisioning.schema.graylog import StreamCreationResponse
from app.customer_provisioning.schema.graylog import TimeBasedIndexSet
from app.customer_provisioning.services.grafana import create_grafana_folder
from app.customer_provisioning.services.grafana import delete_grafana_datasource
from app.customer_provisioning.services.grafana import get_opensearch_version
from app.customers.routes.customers import get_customer
from app.customers.routes.customers import get_customer_meta
from app.db.universal_models import CustomersMeta
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrationsMeta,
)
from app.integrations.office365.schema.provision import PipelineRuleTitles
from app.integrations.office365.schema.provision import PipelineTitles
from app.integrations.office365.schema.provision import ProvisionOffice365AuthKeys
from app.integrations.office365.schema.provision import ProvisionOffice365Response
from app.integrations.office365.services.decommission import (
    decommission_office365_tenant,
)
from app.integrations.routes import create_integration_meta
from app.integrations.schema import CustomerIntegrationsMetaSchema
from app.utils import get_connector_attribute
from app.utils import get_customer_default_settings_attribute

load_dotenv()


############ ! WAZUH MANAGER ! ############
async def get_wazuh_configuration(file_name: str) -> str:
    """
    Retrieves the Wazuh configuration from the manager and writes it to a file.

    Args:
        file_name (str): The name of the file where the configuration data will be written.

    Returns:
        str: The Wazuh configuration data.
    """
    endpoint = "/manager/configuration"
    params = {"raw": True}
    response = await send_get_request(endpoint=endpoint, params=params)
    config_data = response["data"]

    # Get the directory of the current module
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # Create the full file path
    file_path = os.path.join(dir_path, file_name)

    async with aiofiles.open(file_path, "w") as f:
        await f.write(config_data)

    return config_data


async def office365_template_with_api_type(
    customer_code: str,
    provision_office365_auth_keys: ProvisionOffice365AuthKeys,
) -> str:
    """
    Returns a configured Office365 template for Wazuh.

    Args:
        customer_code (str): The customer code.
        provision_office365_auth_keys (ProvisionOffice365AuthKeys): The Office365 auth keys.

    Returns:
        str: The Office365 template configured with the given parameters.
    """

    # Get the directory of the current module
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # Create the full file path
    wazuh_config = os.path.join(dir_path, "wazuh_config.xml")

    # Parse the existing XML file
    tree = parse(wazuh_config)
    root = tree.getroot()

    # Create the office365 element and add it to ossec_config
    office365 = SubElement(root, "office365")

    # Add the child elements to office365
    SubElement(office365, "enabled").text = "yes"
    SubElement(office365, "interval").text = "1m"
    SubElement(office365, "curl_max_size").text = "5M"
    SubElement(office365, "only_future_events").text = "yes"

    # Create the api_auth element and add it to office365
    api_auth = SubElement(office365, "api_auth")

    # Add the customer code as a comment within the api_auth block
    # api_auth.insert(0, Comment(f' Customer Code: {customer_code} '))

    # Add the child elements to api_auth
    SubElement(api_auth, "tenant_id").text = provision_office365_auth_keys.TENANT_ID
    SubElement(api_auth, "client_id").text = provision_office365_auth_keys.CLIENT_ID
    SubElement(api_auth, "client_secret").text = provision_office365_auth_keys.CLIENT_SECRET
    SubElement(api_auth, "api_type").text = provision_office365_auth_keys.API_TYPE

    # Create the subscriptions element and add it to office365
    subscriptions = SubElement(office365, "subscriptions")

    # Add the child elements to subscriptions
    SubElement(subscriptions, "subscription").text = "Audit.SharePoint"
    SubElement(subscriptions, "subscription").text = "Audit.Exchange"
    SubElement(subscriptions, "subscription").text = "DLP.ALL"
    SubElement(subscriptions, "subscription").text = "Audit.General"
    SubElement(subscriptions, "subscription").text = "Audit.AzureActiveDirectory"

    # Convert the office365 element to a string
    office365_str = tostring(office365).decode("utf-8")

    # Pretty print the office365 element
    dom = parseString(office365_str)
    pretty_office365_str = dom.toprettyxml(indent="  ")

    # Remove the XML declaration from the pretty printed office365 string
    pretty_office365_str = pretty_office365_str.replace('<?xml version="1.0" ?>', "").strip()

    # Convert the entire XML to a string
    xml_str = tostring(root).decode("utf-8")

    # Replace the original office365 string with the pretty printed office365 string
    xml_str = xml_str.replace(office365_str, pretty_office365_str)

    # Overwrite the existing XML file with the new contents
    async with aiofiles.open(wazuh_config, "w") as f:
        await f.write(xml_str)

    return xml_str


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


async def add_api_auth_to_office365_block(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> str:
    try:
        # Get the directory of the current module
        dir_path = os.path.dirname(os.path.realpath(__file__))
        # Create the full file path
        wazuh_config = os.path.join(dir_path, "wazuh_config.xml")

        # Parse the existing XML file
        tree = ET.ElementTree()
        tree.parse(wazuh_config)
        root = tree.getroot()

        # Find the office365 block
        office365_block = root.find("office365")

        # If the office365 block exists
        if office365_block is not None:
            # Find the index of the subscriptions block
            subscriptions_index = list(office365_block).index(office365_block.find("subscriptions"))

            # Create a new api_auth block
            api_auth_block = ET.Element("api_auth")

            # Add the tenant_id, client_id, client_secret, and api_type to the api_auth block
            ET.SubElement(api_auth_block, "tenant_id").text = provision_office365_auth_keys.TENANT_ID
            ET.SubElement(api_auth_block, "client_id").text = provision_office365_auth_keys.CLIENT_ID
            ET.SubElement(api_auth_block, "client_secret").text = provision_office365_auth_keys.CLIENT_SECRET
            ET.SubElement(api_auth_block, "api_type").text = provision_office365_auth_keys.API_TYPE

            # Pretty print the new api_auth block
            pretty_api_auth_block = minidom.parseString(ET.tostring(api_auth_block)).toprettyxml(indent="   ")

            # Parse the pretty printed api_auth block back to an Element
            pretty_api_auth_element = ET.fromstring(pretty_api_auth_block)

            # Insert the new pretty printed api_auth block above the subscriptions block
            office365_block.insert(subscriptions_index, pretty_api_auth_element)

            # Convert the modified configuration back to string format
            modified_config = ET.tostring(root, encoding="utf-8").decode("utf-8")

            # Overwrite the existing XML file with the new contents
            with open(wazuh_config, "w") as f:
                f.write(modified_config)

            return modified_config

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error found in ossec.conf. Multiple <ossec_config> blocks found. Remove all additional <ossec_config> blocks and try again.",
        )


async def update_wazuh_configuration(
    provision_office365_auth_keys: ProvisionOffice365AuthKeys,
) -> None:
    """
    Updates the Wazuh configuration. If it fails, remove the <api_type> tag and retry.

    Args:
        provision_office365_auth_keys (ProvisionOffice365AuthKeys): The Office365 authentication keys.
    """
    endpoint = "/manager/configuration"

    # Get the directory of the current module
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # Create the full file path
    wazuh_config_path = os.path.join(dir_path, "wazuh_config.xml")

    # Read the Wazuh configuration from the file
    async with aiofiles.open(wazuh_config_path, "r") as f:
        wazuh_config = await f.read()

    data = wazuh_config.encode("utf-8")

    try:
        # First attempt to update configuration
        response = await send_put_request(
            endpoint=endpoint,
            data=data,
            binary_data=True,
        )
        if response.get("success") and response["data"].get("error") == 0:
            logger.info("Wazuh configuration updated successfully.")
            return
        else:
            logger.error(
                "Failed to update Wazuh configuration. Error: {}".format(response),
            )

    except Exception as e:
        logger.error(f"Exception occurred during Wazuh configuration update: {e}")

    # Remove <api_type> tag and retry
    api_type_tag = f"<api_type>{provision_office365_auth_keys.API_TYPE}</api_type>"
    modified_wazuh_config = wazuh_config.replace(api_type_tag, "")
    data = modified_wazuh_config.encode("utf-8")

    try:
        response = await send_put_request(
            endpoint=endpoint,
            data=data,
            binary_data=True,
        )
        if response.get("success") and response["data"].get("error") == 0:
            logger.info(
                "Wazuh configuration updated successfully after removing <api_type> tag.",
            )
        else:
            logger.error(
                "Failed to update Wazuh configuration after removing <api_type> tag. Error: {}".format(
                    response,
                ),
            )

    except Exception as e:
        logger.error(
            f"Exception occurred during retry of Wazuh configuration update: {e}",
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to update Wazuh configuration.",
        )


async def check_if_office365_is_already_provisioned(
    customer_code: str,
    wazuh_config: str,
) -> bool:
    """
    If the string "Office365 Integration" is found in the Wazuh configuration, return True.

    Args:
        customer_code (str): The customer code.
        wazuh_config (str): The Wazuh configuration in string format.

    Returns:
        bool: True if the Office365 integration is already provisioned, False otherwise.
    """
    if "office365" in wazuh_config:
        return True
    return False


async def check_if_tenant_is_already_provisioned(
    tenant_id: str,
    wazuh_config: str,
) -> None:
    """
    Refuse to provision a Microsoft 365 tenant the Wazuh manager is already polling.

    Wazuh supports several `<api_auth>` blocks in one `<office365>` block, which is how a customer
    with several tenants is configured — but the same tenant twice would have the manager collect
    every event from it twice.

    Args:
        tenant_id (str): The Microsoft 365 tenant (organization) ID.
        wazuh_config (str): The Wazuh configuration in string format.
    """
    if tenant_id in wazuh_config:
        raise HTTPException(
            status_code=400,
            detail=f"Microsoft 365 tenant {tenant_id} is already provisioned on the Wazuh manager.",
        )


async def restart_wazuh_manager() -> None:
    """
    Restarts the Wazuh manager service.
    """
    logger.info("Restarting Wazuh manager service.")
    await send_put_request(endpoint="/manager/restart", data=None)


################## ! GRAYLOG ! ##################


def instance_suffix(instance_name: Optional[str], separator: str = " - ") -> str:
    """Human-readable suffix for titles, empty for the unnamed instance."""
    return f"{separator}{instance_name}" if instance_name else ""


async def build_index_set_config(
    customer_code: str,
    session: AsyncSession,
) -> TimeBasedIndexSet:
    """
    Build the configuration for a time-based index set.

    One index set per customer, shared by every Microsoft 365 tenant they hold. Per-tenant index
    sets are not possible: Graylog rejects any prefix that extends an existing one, so a second
    tenant's `office365-<code>-<tenant>` collides with the first tenant's `office365-<code>` with
    "would conflict with existing index set prefix" (#1117). Sharing is also the right answer on
    its own terms — the tenants belong to one customer, each event still carries its originating
    tenant in `data_office365_OrganizationId`, and the customer's Office365 data stays in one place.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.

    Returns:
        TimeBasedIndexSet: The configured time-based index set.
    """
    # Lowercase the customer code since Graylog index sets must be lowercase
    customer_code = customer_code.lower()
    return TimeBasedIndexSet(
        title=f"{(await get_customer(customer_code, session)).customer.customer_name} - Office365",
        description=f"{customer_code} - Office365",
        index_prefix=f"office365-{customer_code}",
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
        shards=await output_shard_number_to_be_set_based_on_nodes(),
        replicas=0,
        index_optimization_max_num_segments=1,
        index_optimization_disabled=False,
        writable=True,
        field_type_refresh_interval=5000,
    )


# Function to send the POST request and handle the response
async def send_index_set_creation_request(
    index_set: TimeBasedIndexSet,
) -> GraylogIndexSetCreationResponse:
    """
    Sends a request to create an index set in Graylog.

    Args:
        index_set (TimeBasedIndexSet): The index set to be created.

    Returns:
        GraylogIndexSetCreationResponse: The response from Graylog after creating the index set.
    """
    json_index_set = json.dumps(index_set.model_dump())
    logger.info(f"json_index_set set: {json_index_set}")
    response_json = await send_post_request(
        endpoint="/api/system/indices/index_sets",
        data=index_set.model_dump(),
    )
    return GraylogIndexSetCreationResponse(**response_json)


# Refactored create_index_set function
async def create_index_set(
    customer_code: str,
    session: AsyncSession,
) -> GraylogIndexSetCreationResponse:
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
async def build_event_stream_config(
    customer_code: str,
    provision_office365_auth_keys: ProvisionOffice365AuthKeys,
    index_set_id: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> Office365EventStream:
    """
    Build the configuration for a Wazuh event stream.

    A stream rule pins exactly one organization ID and Graylog cannot OR several values together in
    an AND-matched stream, so a customer with several Microsoft 365 tenants gets one stream per
    tenant, all writing into that customer's single Office365 index set. The instance label is put
    in the title so the streams are tellable apart in Graylog.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.
        instance_name (Optional[str]): The instance label of the tenant being provisioned.

    Returns:
        Office365EventStream: The configured Wazuh event stream.
    """
    customer_name = (await get_customer(customer_code, session)).customer.customer_name
    stream_title = f"{customer_name} - Office365" + (f" - {instance_name}" if instance_name else "")
    return Office365EventStream(
        title=stream_title,
        description=stream_title,
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
            },
        ],
        matching_type="AND",
        remove_matches_from_default_stream=True,
        content_pack=None,
    )


async def send_event_stream_creation_request(
    event_stream: Office365EventStream,
) -> StreamCreationResponse:
    """
    Sends a request to create an event stream.

    Args:
        event_stream (WazuhEventStream): The event stream to be created.

    Returns:
        StreamCreationResponse: The response containing the created event stream.
    """
    json_event_stream = json.dumps(event_stream.model_dump())
    logger.info(f"json_event_stream set: {json_event_stream}")
    response_json = await send_post_request_create_entity(
        endpoint="/api/streams",
        entity=event_stream.model_dump(),
    )
    return StreamCreationResponse(**response_json)


async def create_event_stream(
    customer_code: str,
    provision_office365_auth_keys: ProvisionOffice365AuthKeys,
    index_set_id: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> StreamCreationResponse:
    """
    Creates an event stream for a customer.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        index_set_id (str): The ID of the index set.

    Returns:
        The result of the event stream creation request.
    """
    event_stream_config = await build_event_stream_config(
        customer_code,
        provision_office365_auth_keys,
        index_set_id,
        session,
        instance_name=instance_name,
    )
    return await send_event_stream_creation_request(event_stream_config)


############### ! PIPELINES AND RULES ! ################


# ! PIPELINE RULES ! #
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
        "Office365 Syslog Type": create_office365_syslog_type_rule,
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
        f'rule "{rule_title}"\n'
        "when\n"
        '  has_field("data_office365_CreationTime")\n'
        "then\n"
        "  let creation_time = $message.data_office365_CreationTime;\n"
        '  set_field("timestamp_utc", creation_time);\n'
        "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


async def create_office365_syslog_type_rule(rule_title: str) -> None:
    """
    Creates the 'Office365 Syslog Type' pipeline rule.
    """
    rule_source = (
        f'rule "{rule_title}"\n'
        "when\n"
        '  $message.rule_group1 == "office365"\n'
        "then\n"
        '  set_field("syslog_type", "office365");\n'
        "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


async def create_wazuh_info_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - INFO' pipeline rule.
    """
    rule_source = (
        f'rule "{rule_title}"\n'
        "when\n"
        "  to_long($message.rule_level) > 0 AND to_long($message.rule_level) < 4\n"
        "then\n"
        '  set_field("syslog_level", "INFO");\n'
        "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


async def create_wazuh_warning_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - WARNING' pipeline rule.
    """
    rule_source = (
        f'rule "{rule_title}"\n'
        "when\n"
        "  to_long($message.rule_level) > 7 AND to_long($message.rule_level) < 12\n"
        "then\n"
        '  set_field("syslog_level", "WARNING");\n'
        "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


async def create_wazuh_notice_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE' pipeline rule.
    """
    rule_source = (
        f'rule "{rule_title}"\n'
        "when\n"
        "  to_long($message.rule_level) > 3 AND to_long($message.rule_level) < 8\n"
        "then\n"
        '  set_field("syslog_level", "NOTICE");\n'
        "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


async def create_wazuh_alert_rule(rule_title: str) -> None:
    """
    Creates the 'WAZUH CREATE FIELD SYSLOG LEVEL - ALERT' pipeline rule.
    """
    rule_source = (
        f'rule "{rule_title}"\n' "when\n" "  to_long($message.rule_level) > 11\n" "then\n" '  set_field("syslog_level", "ALERT");\n' "end"
    )
    await create_pipeline_rule(
        CreatePipelineRule(
            title=rule_title,
            description=rule_title,
            source=rule_source,
        ),
    )


# ! PIPELINE ! #
async def check_pipeline() -> None:
    """
    Checks if the pipeline exists in Graylog. If it doesn't, create it.
    """
    pipelines = await get_pipelines()
    non_existing_pipelines = await pipeline_exists(pipelines)
    if non_existing_pipelines:
        logger.info(f"Creating pipelines: {non_existing_pipelines}")
        await create_pipeline(non_existing_pipelines)


async def pipeline_exists(pipelines: GraylogPipelinesResponse) -> List[str]:
    """
    Checks if the pipeline exists in Graylog and returns a list of non-existing pipelines.
    """
    return [
        pipeline_title.value
        for pipeline_title in PipelineTitles
        if not any(pipeline.title == pipeline_title.value for pipeline in pipelines.pipelines)
    ]


async def create_pipeline(non_existing_pipelines: List[str]) -> None:
    """
    Creates the given pipeline.
    """
    pipeline_creators = {
        "OFFICE365 PROCESSING PIPELINE": create_office365_pipeline,
    }

    for pipeline_title in non_existing_pipelines:
        logger.info(f"Creating pipeline {pipeline_title}.")
        await pipeline_creators[pipeline_title](pipeline_title)


async def create_office365_pipeline(pipeline_title: str) -> None:
    """
    Creates the 'OFFICE365 PROCESSING PIPELINE' pipeline.
    """
    pipeline_description = "OFFICE365 PROCESSING PIPELINE"
    pipeline_source = (
        'pipeline "OFFICE365 PROCESSING PIPELINE"\n'
        "stage 0 match either\n"
        'rule "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT"\n'
        'rule "WAZUH CREATE FIELD SYSLOG LEVEL - INFO"\n'
        'rule "WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE"\n'
        'rule "WAZUH CREATE FIELD SYSLOG LEVEL - WARNING"\n'
        'rule "Office365 Timestamp - UTC"\n'
        'rule "SYSLOG TYPE OFFICE365"\n'
        "end"
    )
    await create_pipeline_graylog(
        CreatePipeline(
            title=pipeline_title,
            description=pipeline_description,
            source=pipeline_source,
        ),
    )


#### ! GRAFANA ! ####
async def create_grafana_datasource(
    customer_code: str,
    session: AsyncSession,
) -> GrafanaDataSourceCreationResponse:
    """
    Creates a Grafana Wazuh datasource for a new customer using the OpenSearch Data Source.

    One datasource per customer, like the index set it reads. Every Microsoft 365 tenant of a
    customer writes into `office365-<customer_code>`, so a per-tenant datasource would have nothing
    of its own to point at.

    Args:
        request (ProvisionNewCustomer): The request object containing customer information.
        organization_id (int): The ID of the organization to create the datasource for.
        session (AsyncSession): The database session.

    Returns:
        GrafanaDataSourceCreationResponse: The response object containing the result of the datasource creation.
    """
    logger.info("Creating Grafana datasource")
    # Lowercase the customer code since Graylog index sets must be lowercase
    customer_code = customer_code.lower()
    datasource_name = "O365"
    index_pattern = f"office365-{customer_code}*"
    grafana_client = await create_grafana_client("Grafana")
    grafana_url = await get_connector_attribute(
        connector_id=12,
        column_name="connector_url",
        session=session,
    )
    # Switch to the newly created organization
    grafana_client.user.switch_actual_user_organisation(
        (await get_customer_meta(customer_code, session)).customer_meta.customer_meta_grafana_org_id,
    )
    datasource_payload = GrafanaDatasource(
        name=datasource_name,
        type="grafana-opensearch-datasource",
        typeName="OpenSearch",
        access="proxy",
        url=await get_connector_attribute(
            connector_id=1,
            column_name="connector_url",
            session=session,
        ),
        database=index_pattern,
        basicAuth=True,
        basicAuthUser=await get_connector_attribute(
            connector_id=1,
            column_name="connector_username",
            session=session,
        ),
        secureJsonData={
            "basicAuthPassword": await get_connector_attribute(
                connector_id=1,
                column_name="connector_password",
                session=session,
            ),
        },
        isDefault=False,
        jsonData={
            "dataLinks": [
                {
                    "field": "^_id$",
                    "url": (
                        "{}/explore?left=%7B%22datasource%22:%22{}%22,%22queries%22:%5B%7B"
                        "%22refId%22:%22A%22,%22query%22:%22_id:${{__value.raw}}%22,%22alias%22:%22%22,"
                        "%22metrics%22:%5B%7B%22id%22:%221%22,%22type%22:%22logs%22,%22settings%22:"
                        "%7B%22limit%22:%22500%22%7D%7D%5D,%22bucketAggs%22:%5B%7B%22type%22:%22date_histogram%22,%22id%22:%221%22,%22settings%22:%7B%22interval%22:%22auto%22%7D%7D%5D,%22timeField%22:"
                        "%22timestamp%22%7D%5D,%22range%22:%7B%22from%22:%22now-6h%22,%22to%22:%22now%22%7D%7D"
                    ).format(grafana_url, quote(datasource_name, safe="")),
                },
            ],
            "database": index_pattern,
            "flavor": "opensearch",
            "includeFrozen": False,
            "logLevelField": "syslog_level",
            "logMessageField": "rule_description",
            "maxConcurrentShardRequests": 5,
            "pplEnabled": True,
            "timeField": "timestamp",
            "tlsSkipVerify": True,
            "version": await get_opensearch_version(),
        },
        readOnly=True,
    )
    results = grafana_client.datasource.create_datasource(
        datasource=datasource_payload.model_dump(),
    )
    return GrafanaDataSourceCreationResponse(**results)


################## ! MAIN FUNCTION ! ##################


class _ProvisioningRollback:
    """Undo whatever a failed deployment already created.

    Deployment touches the Wazuh manager, Graylog and Grafana before it records anything in the
    database, so a failure partway used to leave all of it behind while the integration still
    showed a Deploy button. Worse, the leftover `<api_auth>` block made the retry *impossible*:
    `check_if_tenant_is_already_provisioned` saw the tenant in ossec.conf and refused with "already
    provisioned on the Wazuh manager" (#1117).

    Steps are undone newest-first, and one failing undo never stops the rest — a rollback that
    gives up halfway is what created the mess it is trying to clean up.
    """

    def __init__(self, customer_code: str, instance_name: Optional[str]):
        self._steps: List[tuple] = []
        self._customer_code = customer_code
        self._instance_name = instance_name

    def add(self, description: str, undo) -> None:
        self._steps.append((description, undo))

    async def run(self) -> List[str]:
        """Undo every recorded step; returns the descriptions that could not be undone."""
        failures = []
        for description, undo in reversed(self._steps):
            try:
                logger.info(f"Rolling back: {description}")
                await undo()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Could not roll back {description}: {exc}")
                failures.append(f"{description} ({exc})")
        return failures


async def provision_office365(
    customer_code: str,
    provision_office365_auth_keys: ProvisionOffice365AuthKeys,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> ProvisionOffice365Response:
    """
    Provision one Microsoft 365 tenant for a customer.

    A customer may hold several tenants (an MSSP customer with subsidiaries or acquisitions), each
    its own `customer_integrations` instance. What is created *per tenant* is the Wazuh
    `<api_auth>` block and the Graylog stream, whose rule pins that tenant's organization ID. What
    is created once and shared by every tenant of the customer is the Graylog index set and the
    Grafana datasource, folder and dashboards.

    Sharing the index set is not just a simplification: Graylog refuses an index prefix that
    extends an existing one, so a per-tenant `office365-<code>-<tenant>` is rejected outright
    against the first tenant's `office365-<code>`. It is also the behaviour that matches the
    feature — the tenants belong to one customer, and each event keeps its originating tenant in
    `data_office365_OrganizationId`.

    Either the whole deployment succeeds or it leaves nothing behind: every externally-visible
    step registers its undo, and any failure rolls them back before the error reaches the caller.
    """
    logger.info(
        f"Provisioning Office365 integration for customer {customer_code} (instance: {instance_name or 'default'}).",
    )

    rollback = _ProvisioningRollback(customer_code, instance_name)

    try:
        # Get Wazuh configuration
        wazuh_config = await get_wazuh_configuration(file_name="wazuh_config.xml")

        # Check if Office365 is already provisioned
        office365_provisioned = await check_if_office365_is_already_provisioned(customer_code, wazuh_config)

        # Refuse a tenant the manager is already polling, whoever it belongs to
        await check_if_tenant_is_already_provisioned(provision_office365_auth_keys.TENANT_ID, wazuh_config)

        if office365_provisioned:
            # An <office365> block exists (this deployment already collects for some tenant), so this
            # tenant is added as another <api_auth> inside it — Wazuh's own multi-tenant shape.
            logger.info("Office365 block already exists on the manager; adding this tenant's api_auth block.")
            wazuh_config = await add_api_auth_to_office365_block(customer_code, provision_office365_auth_keys)
        else:
            logger.info("Office365 integration is not yet provisioned.")
            logger.info("Creating new Office365 block.")
            office365_templated = await office365_template_with_api_type(
                customer_code,
                provision_office365_auth_keys,
            )
            # Append Office365 template to Wazuh configuration
            wazuh_config = await append_office365_template(wazuh_config, office365_templated)

        # Update Wazuh configuration
        await update_wazuh_configuration(provision_office365_auth_keys)
        rollback.add(
            f"the Wazuh api_auth block for tenant {provision_office365_auth_keys.TENANT_ID}",
            lambda: decommission_office365_tenant(customer_code, provision_office365_auth_keys.TENANT_ID),
        )

        # Restart Wazuh manager
        await restart_wazuh_manager()

        # Graylog Deployment
        await check_pipeline_rules()
        await check_pipeline()

        # Anything this customer's earlier tenants already provisioned is reused rather than
        # recreated: they all write into one index set and are read through one Grafana datasource.
        existing_meta = await get_existing_office365_meta(customer_code, session)

        if existing_meta and existing_meta.graylog_index_id:
            index_set_id = existing_meta.graylog_index_id
            logger.info(f"Reusing this customer's Office365 index set: {index_set_id}")
        else:
            index_set_id = (await create_index_set(customer_code=customer_code, session=session)).data.id
            logger.info(f"Index set: {index_set_id}")
            rollback.add(f"Graylog index set {index_set_id}", lambda: delete_index_by_id(index_id=index_set_id))

        # Create event stream — always per tenant, because its rule pins one organization ID
        stream_id = (
            await create_event_stream(
                customer_code,
                provision_office365_auth_keys,
                index_set_id,
                session,
                instance_name=instance_name,
            )
        ).data.stream_id
        rollback.add(f"Graylog stream {stream_id}", lambda: delete_stream(stream_id=stream_id))

        pipeline_id = await get_pipeline_id(subscription="OFFICE365")
        # Combine stream and pipeline IDs
        stream_and_pipeline = StreamConnectionToPipelineRequest(
            stream_id=stream_id,
            pipeline_ids=pipeline_id,
        )
        # Connect stream to pipeline
        logger.info(f"Stream and pipeline: {stream_and_pipeline}")
        await connect_stream_to_pipeline(stream_and_pipeline)
        # Start stream
        await start_stream(stream_id=stream_id)

        # Grafana Deployment
        grafana_org_id = (await get_customer_meta(customer_code, session)).customer_meta.customer_meta_grafana_org_id

        if existing_meta and existing_meta.grafana_datasource_uid and existing_meta.grafana_dashboard_folder_id:
            office365_datasource_uid = existing_meta.grafana_datasource_uid
            grafana_o365_folder_id = existing_meta.grafana_dashboard_folder_id
            logger.info(
                f"Reusing this customer's Office365 Grafana folder {grafana_o365_folder_id} " f"and datasource {office365_datasource_uid}.",
            )
        else:
            office365_datasource_uid = (
                await create_grafana_datasource(
                    customer_code=customer_code,
                    session=session,
                )
            ).datasource.uid
            rollback.add(
                f"Grafana datasource {office365_datasource_uid}",
                lambda: delete_grafana_datasource(
                    organization_id=grafana_org_id,
                    datasource_uid=office365_datasource_uid,
                ),
            )

            grafana_o365_folder_id = (
                await create_grafana_folder(
                    organization_id=grafana_org_id,
                    folder_title="OFFICE 365",
                )
            ).id
            rollback.add(
                f"Grafana folder {grafana_o365_folder_id}",
                lambda: delete_folder(grafana_org_id, grafana_o365_folder_id),
            )

            await provision_dashboards(
                DashboardProvisionRequest(
                    dashboards=[dashboard.name for dashboard in Office365Dashboard],
                    organizationId=grafana_org_id,
                    folderId=grafana_o365_folder_id,
                    datasourceUid=office365_datasource_uid,
                    grafana_url=(await get_customer_default_settings_attribute(column_name="grafana_url", session=session))
                    or "grafana.company.local",
                ),
            )

        # The metadata entry is written *before* the integration is flagged as deployed: the UI
        # hides the Deploy button once `deployed` is true, so a failure here would otherwise leave
        # the integration undeployable and its infrastructure untracked.
        await create_integration_meta_entry(
            CustomerIntegrationsMetaSchema(
                customer_code=customer_code,
                integration_name="Office365",
                instance_name=instance_name,
                graylog_input_id=None,
                graylog_index_id=index_set_id,
                graylog_stream_id=stream_id,
                grafana_org_id=grafana_org_id,
                grafana_dashboard_folder_id=grafana_o365_folder_id,
                grafana_datasource_uid=office365_datasource_uid,
            ),
            session,
        )

        await update_customer_integration_table(customer_code, session, instance_name=instance_name)
        await update_customermeta_table(customer_code, session, provision_office365_auth_keys.TENANT_ID)

    except Exception as exc:
        logger.error(f"Office365 provisioning failed for customer {customer_code}: {exc}. Rolling back.")
        failures = await rollback.run()

        detail = getattr(exc, "detail", None) or str(exc)
        message = f"Office365 deployment failed and was rolled back: {detail}"
        if failures:
            message += " Some resources could not be removed automatically: " + "; ".join(failures) + "."

        # The original status is preserved where there is one, so a 400 from a validation-style
        # failure does not become a 500 just because it was rolled back.
        raise HTTPException(status_code=getattr(exc, "status_code", 500), detail=message)

    return ProvisionOffice365Response(
        success=True,
        message=(
            f"Successfully provisioned Office365 integration for customer {customer_code}"
            + (f" (tenant {instance_name})." if instance_name else ".")
        ),
    )


######### ! Update Database ! ############
async def get_existing_office365_meta(
    customer_code: str,
    session: AsyncSession,
) -> Optional[CustomerIntegrationsMeta]:
    """
    Return the metadata of an Office365 instance this customer already has deployed, if any.

    Its index set and Grafana resources are shared with every further tenant of the same customer,
    so this is what tells provisioning to reuse rather than create — and, on the delete path, what
    must survive while any sibling instance is still deployed.
    """
    result = await session.execute(
        select(CustomerIntegrationsMeta).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == "Office365",
        ),
    )
    return result.scalars().first()


async def update_customer_integration_table(
    customer_code: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> None:
    """
    Updates the `customer_integrations` table to set the `deployed` column to True where the `customer_code`
    matches the given customer code and the `integration_service_name` is "Office365".

    Scoped to one instance so deploying a customer's second Microsoft 365 tenant does not mark
    their other, still-undeployed tenants as deployed — which would hide the Deploy button for them.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The async session object for making HTTP requests.
        instance_name (Optional[str]): The instance being deployed.
    """
    instance_clause = (
        CustomerIntegrations.instance_name.is_(None) if instance_name is None else CustomerIntegrations.instance_name == instance_name
    )
    await session.execute(
        update(CustomerIntegrations)
        .where(
            and_(
                CustomerIntegrations.customer_code == customer_code,
                CustomerIntegrations.integration_service_name == "Office365",
                instance_clause,
            ),
        )
        .values(deployed=True),
    )
    await session.commit()

    return None


async def update_customermeta_table(customer_code: str, session: AsyncSession, tenant_id: str) -> None:
    """
    Updates the `customer_meta` table to set the `office365_tenant_id` column to the given tenant_id.

    The column holds a single tenant and predates multi-tenant support, so it is only written while
    still empty — the customer's first tenant claims it and later ones leave it alone. Alert routing
    for every tenant goes through the stored TENANT_ID auth keys instead
    (`resolve_customer_code_from_office365_tenant`), so nothing depends on this column being the
    "current" tenant.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The async session object for making HTTP requests.
    """
    await session.execute(
        update(CustomersMeta)
        .where(
            CustomersMeta.customer_code == customer_code,
            (CustomersMeta.customer_meta_office365_organization_id.is_(None))
            | (CustomersMeta.customer_meta_office365_organization_id == ""),
        )
        .values(customer_meta_office365_organization_id=tenant_id),
    )
    await session.commit()

    return None


async def create_integration_meta_entry(
    customer_integration_meta: CustomerIntegrationsMetaSchema,
    session: AsyncSession,
) -> None:
    """
    Creates an entry for the customer integration meta in the database.

    Args:
        customer_integration_meta (CustomerIntegrationsMetaSchema): The customer integration meta object.
        session (AsyncSession): The async session object for database operations.
    """
    await create_integration_meta(customer_integration_meta, session)
    logger.info(
        f"Integration meta entry created for customer {customer_integration_meta.customer_code}.",
    )
