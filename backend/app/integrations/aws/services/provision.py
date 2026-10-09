"""Provisioning one AWS account (integration instance) for a customer.

Modelled on Office365 (`app/integrations/office365/services/provision.py`), with one structural
difference: an AWS instance has several *services* (CloudTrail, GuardDuty, …), each with its own
index set, stream and Grafana datasource. What is created where:

* **Per instance** (one AWS account + bucket): its `<bucket>` entries in the aws-s3 wodle, and one
  Graylog stream per service, pinned to the bucket, the service and the account.
* **Per customer and service**, shared by every AWS account of the customer: the `<service>-<code>`
  index set and its Grafana datasource. Graylog refuses an index prefix that extends an existing one
  (#1117), so per-account index sets are not an option — and every event still names its account.
* **Per customer**: the "AWS" Grafana folder.

`provision_aws` is also the re-sync path for an instance that is already deployed: it reconciles the
manager, Graylog and Grafana with the instance's current auth keys, which covers key rotation and
adding or removing a service. The account, the bucket and a service's prefix identify what was
deployed, so changing those means deleting the instance and adding it again.

Either the deployment completes or it leaves nothing behind (see `_ProvisioningRollback`).
"""

import json
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from urllib.parse import quote

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.grafana.services.folders import delete_folder
from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.graylog.schema.pipelines import CreatePipeline
from app.connectors.graylog.schema.pipelines import CreatePipelineRule
from app.connectors.graylog.services.management import delete_index_by_id
from app.connectors.graylog.services.management import start_stream
from app.connectors.graylog.services.pipelines import connect_stream_to_pipeline
from app.connectors.graylog.services.pipelines import create_pipeline_graylog
from app.connectors.graylog.services.pipelines import create_pipeline_rule
from app.connectors.graylog.services.pipelines import get_pipeline_rules
from app.connectors.graylog.services.pipelines import get_pipelines
from app.connectors.graylog.services.streams import delete_stream
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_post_request_create_entity
from app.connectors.graylog.utils.universal import (
    send_put_request as send_graylog_put_request,
)
from app.connectors.wazuh_indexer.services.monitoring import (
    output_shard_number_to_be_set_based_on_nodes,
)
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
from app.integrations.aws.schema.provision import AWS_INTEGRATION_NAME
from app.integrations.aws.schema.provision import PipelineRuleTitles
from app.integrations.aws.schema.provision import PipelineTitles
from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys
from app.integrations.aws.schema.provision import ProvisionAwsResponse
from app.integrations.aws.services.account_lookup import list_aws_instances
from app.integrations.aws.services.decommission import remove_service_resources
from app.integrations.aws.services.validate import AwsValidationError
from app.integrations.aws.services.validate import validate_aws_access
from app.integrations.aws.services.wazuh_config import desired_buckets
from app.integrations.aws.services.wazuh_manager import apply_instance_buckets
from app.integrations.aws.services.wazuh_manager import aws_config_notice
from app.integrations.aws.services.wazuh_manager import log_markers
from app.integrations.aws.services.wazuh_manager import wait_for_profile_error
from app.integrations.aws.utils.services import AWS_SERVICES
from app.integrations.aws.utils.services import AwsServiceDefinition
from app.integrations.aws.utils.services import decode_service_ids
from app.integrations.aws.utils.services import encode_service_ids
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrationsMeta,
)
from app.integrations.office365.services.provision import create_wazuh_alert_rule
from app.integrations.office365.services.provision import create_wazuh_info_rule
from app.integrations.office365.services.provision import create_wazuh_notice_rule
from app.integrations.office365.services.provision import create_wazuh_warning_rule
from app.utils import get_connector_attribute

GRAFANA_FOLDER_TITLE = "AWS"


################## ! ACCOUNT OWNERSHIP ! ##################


async def ensure_account_is_free(
    customer_code: str,
    instance_name: Optional[str],
    provision_aws_auth_keys: ProvisionAwsAuthKeys,
    session: AsyncSession,
) -> None:
    """
    Refuse an AWS account another customer owns, or a bucket + account another instance collects.

    Alerts are routed to a customer by account ID (`resolve_customer_code_from_aws_account`), so one
    account must belong to one customer. Within a customer, one account may appear in several
    instances — CloudTrail and GuardDuty often export to different buckets — but bucket + account is
    what identifies an instance's `<bucket>` entries on the manager, so that pair must be unique.
    """
    account_id = provision_aws_auth_keys.AWS_ACCOUNT_ID
    for record in await list_aws_instances(session):
        if record.customer_code == customer_code and record.instance_name == instance_name:
            continue
        if record.account_id != account_id:
            continue
        if record.customer_code != customer_code:
            raise HTTPException(
                status_code=400,
                detail=f"AWS account {account_id} is already configured for customer {record.customer_code}.",
            )
        if record.bucket_name == provision_aws_auth_keys.BUCKET_NAME:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"AWS account {account_id} with bucket {record.bucket_name} is already configured as this customer's "
                    f"'{record.instance_name or 'Default'}' AWS instance."
                ),
            )


################## ! GRAYLOG ! ##################


def build_index_set_config(
    customer_code: str,
    customer_name: str,
    definition: AwsServiceDefinition,
    shards: int,
) -> TimeBasedIndexSet:
    """One index set per customer and service, e.g. `cloudtrail-<code>`; see the module docstring."""
    customer_code = customer_code.lower()
    return TimeBasedIndexSet(
        title=f"{customer_name} - AWS {definition.title}",
        description=f"{customer_code} - AWS {definition.title}",
        index_prefix=f"{definition.key}-{customer_code}",
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
        shards=shards,
        replicas=0,
        index_optimization_max_num_segments=1,
        index_optimization_disabled=False,
        writable=True,
        field_type_refresh_interval=5000,
    )


async def create_index_set(
    customer_code: str,
    definition: AwsServiceDefinition,
    session: AsyncSession,
) -> str:
    customer_name = (await get_customer(customer_code, session)).customer.customer_name
    index_set = build_index_set_config(customer_code, customer_name, definition, await output_shard_number_to_be_set_based_on_nodes())
    logger.info(f"Creating Graylog index set {index_set.index_prefix} for customer {customer_code}.")
    response_json = await send_post_request(
        endpoint="/api/system/indices/index_sets",
        data=index_set.model_dump(),
    )
    return GraylogIndexSetCreationResponse(**response_json).data.id


def build_stream_rules(definition: AwsServiceDefinition, bucket_name: str, account_id: str) -> List[dict]:
    """
    The AND-matched rules that route one instance's events of one service to its stream.

    AWS events come from the Wazuh master (agent 000) and carry no agent customer label, so the
    stream routes on AWS fields: the bucket, the service, and the account — the account so that one
    bucket shared by several accounts (an organization trail) stays separated per account.
    """
    return [
        {"field": "data_aws_log_info_s3bucket", "type": 1, "inverted": False, "value": bucket_name},
        {"field": "data_aws_source", "type": 1, "inverted": False, "value": definition.key},
        {"field": definition.account_field, "type": 1, "inverted": False, "value": account_id},
    ]


def build_event_stream_config(
    customer_name: str,
    definition: AwsServiceDefinition,
    provision_aws_auth_keys: ProvisionAwsAuthKeys,
    index_set_id: str,
    instance_name: Optional[str] = None,
) -> Office365EventStream:
    # `Office365EventStream` is the generic stream shape despite its name.
    title = f"{customer_name} - AWS {definition.title}" + (f" - {instance_name}" if instance_name else "")
    return Office365EventStream(
        title=title,
        description=title,
        index_set_id=index_set_id,
        rules=build_stream_rules(definition, provision_aws_auth_keys.BUCKET_NAME, provision_aws_auth_keys.AWS_ACCOUNT_ID),
        matching_type="AND",
        remove_matches_from_default_stream=True,
        content_pack=None,
    )


async def create_event_stream(
    customer_code: str,
    definition: AwsServiceDefinition,
    provision_aws_auth_keys: ProvisionAwsAuthKeys,
    index_set_id: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> str:
    customer_name = (await get_customer(customer_code, session)).customer.customer_name
    stream = build_event_stream_config(customer_name, definition, provision_aws_auth_keys, index_set_id, instance_name)
    logger.info(f"Creating Graylog stream: {json.dumps(stream.model_dump())}")
    response_json = await send_post_request_create_entity(endpoint="/api/streams", entity=stream.model_dump())
    return StreamCreationResponse(**response_json).data.stream_id


async def connect_and_start_stream(stream_id: str, pipeline_id: str) -> None:
    await connect_stream_to_pipeline(StreamConnectionToPipelineRequest(stream_id=stream_id, pipeline_ids=[pipeline_id]))
    await start_stream(stream_id=stream_id)


############### ! PIPELINES AND RULES ! ################


def _fallback_chain(fields: List[str]) -> str:
    """`to_string($message.a, to_string($message.b))` — the first of the fields that is present."""
    expression = f"to_string($message.{fields[-1]})"
    for name in reversed(fields[:-1]):
        expression = f"to_string($message.{name}, {expression})"
    return expression


def _unique(values) -> List[str]:
    return list(dict.fromkeys(values))


def aws_rule_sources() -> Dict[str, str]:
    """
    The AWS pipeline rules, generated from `AWS_SERVICES` so a new service needs no rule edits.

    - `SYSLOG TYPE AWS`: makes the incident-management source `aws` (the events arrive as `wazuh`).
    - `AWS Timestamp - UTC`: the event's own time — CloudTrail's `eventTime`, GuardDuty's `updatedAt`.
    - `AWS ACCOUNT ID`: one `aws_account_id` field whatever the service calls it; this is the field
      the account is resolved to a customer from.
    """
    timestamp_fields = _unique(definition.timestamp_field for definition in AWS_SERVICES.values())
    account_fields = _unique(definition.account_field for definition in AWS_SERVICES.values())

    def when_any(fields: List[str]) -> str:
        return " OR ".join(f'has_field("{name}")' for name in fields)

    return {
        PipelineRuleTitles.AWS_SYSLOG_TYPE.value: (
            f'rule "{PipelineRuleTitles.AWS_SYSLOG_TYPE.value}"\n'
            "when\n"
            '  to_string($message.data_integration) == "aws"\n'
            "then\n"
            '  set_field("syslog_type", "aws");\n'
            "end"
        ),
        PipelineRuleTitles.AWS_TIMESTAMP.value: (
            f'rule "{PipelineRuleTitles.AWS_TIMESTAMP.value}"\n'
            "when\n"
            f"  {when_any(timestamp_fields)}\n"
            "then\n"
            f'  set_field("timestamp_utc", {_fallback_chain(timestamp_fields)});\n'
            "end"
        ),
        PipelineRuleTitles.AWS_ACCOUNT_ID.value: (
            f'rule "{PipelineRuleTitles.AWS_ACCOUNT_ID.value}"\n'
            "when\n"
            f"  {when_any(account_fields)}\n"
            "then\n"
            f'  set_field("aws_account_id", {_fallback_chain(account_fields)});\n'
            "end"
        ),
    }


def aws_pipeline_source() -> str:
    rules = "\n".join(f'rule "{title.value}"' for title in PipelineRuleTitles)
    return f'pipeline "{PipelineTitles.AWS.value}"\nstage 0 match either\n{rules}\nend'


def _same_source(a: Optional[str], b: str) -> bool:
    return " ".join((a or "").split()) == " ".join(b.split())


async def ensure_pipeline_rules() -> None:
    """
    Create missing rules and bring CoPilot's own AWS rules up to date.

    The WAZUH SYSLOG LEVEL rules are shared with other integrations and only created when missing.
    The AWS rules belong to this integration, so a rule whose source differs from what
    `aws_rule_sources` generates — typically because a service was added — is rewritten in place.
    """
    existing = {rule.title: rule for rule in (await get_pipeline_rules()).pipeline_rules}

    shared_creators = {
        PipelineRuleTitles.WAZUH_INFO.value: create_wazuh_info_rule,
        PipelineRuleTitles.WAZUH_WARNING.value: create_wazuh_warning_rule,
        PipelineRuleTitles.WAZUH_NOTICE.value: create_wazuh_notice_rule,
        PipelineRuleTitles.WAZUH_ALERT.value: create_wazuh_alert_rule,
    }
    for title, creator in shared_creators.items():
        if title not in existing:
            logger.info(f"Creating pipeline rule {title}.")
            await creator(title)

    for title, source in aws_rule_sources().items():
        rule = existing.get(title)
        if rule is None:
            logger.info(f"Creating pipeline rule {title}.")
            await create_pipeline_rule(CreatePipelineRule(title=title, description=title, source=source))
        elif not _same_source(rule.source, source):
            logger.info(f"Updating pipeline rule {title}.")
            result = await send_graylog_put_request(
                endpoint=f"/api/system/pipelines/rule/{rule.id}",
                data={"title": title, "description": rule.description or title, "source": source},
            )
            if not result or not result.get("success"):
                raise HTTPException(
                    status_code=502,
                    detail=f"Could not update Graylog pipeline rule {title}: {(result or {}).get('message')}",
                )


async def ensure_pipeline() -> str:
    """Create (or bring up to date) the AWS processing pipeline; returns its ID."""
    title = PipelineTitles.AWS.value
    source = aws_pipeline_source()

    pipeline = next((p for p in (await get_pipelines()).pipelines if p.title == title), None)
    if pipeline is None:
        logger.info(f"Creating pipeline {title}.")
        await create_pipeline_graylog(CreatePipeline(title=title, description=title, source=source))
        pipeline = next((p for p in (await get_pipelines()).pipelines if p.title == title), None)
        if pipeline is None:
            raise HTTPException(status_code=502, detail=f"Graylog did not create the pipeline {title}.")
    elif not _same_source(pipeline.source, source):
        logger.info(f"Updating pipeline {title}.")
        result = await send_graylog_put_request(
            endpoint=f"/api/system/pipelines/pipeline/{pipeline.id}",
            data={"title": title, "description": pipeline.description or title, "source": source},
        )
        if not result or not result.get("success"):
            raise HTTPException(status_code=502, detail=f"Could not update Graylog pipeline {title}: {(result or {}).get('message')}")
    return pipeline.id


#### ! GRAFANA ! ####


async def create_grafana_datasource(
    customer_code: str,
    definition: AwsServiceDefinition,
    grafana_org_id: str,
    session: AsyncSession,
) -> str:
    """
    Create the OpenSearch datasource for one AWS service of a customer, on `<service>-<code>*`.

    One per customer and service, like the index set it reads. Returns the datasource UID.
    """
    customer_code = customer_code.lower()
    datasource_name = f"AWS {definition.title.upper()}"
    index_pattern = f"{definition.key}-{customer_code}*"
    grafana_client = await create_grafana_client("Grafana")
    grafana_url = await get_connector_attribute(connector_id=12, column_name="connector_url", session=session)
    grafana_client.user.switch_actual_user_organisation(grafana_org_id)
    datasource_payload = GrafanaDatasource(
        name=datasource_name,
        type="grafana-opensearch-datasource",
        typeName="OpenSearch",
        access="proxy",
        url=await get_connector_attribute(connector_id=1, column_name="connector_url", session=session),
        database=index_pattern,
        basicAuth=True,
        basicAuthUser=await get_connector_attribute(connector_id=1, column_name="connector_username", session=session),
        secureJsonData={
            "basicAuthPassword": await get_connector_attribute(connector_id=1, column_name="connector_password", session=session),
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
    results = grafana_client.datasource.create_datasource(datasource=datasource_payload.model_dump())
    return GrafanaDataSourceCreationResponse(**results).datasource.uid


################## ! MAIN FUNCTION ! ##################


class _ProvisioningRollback:
    """Undo whatever a failed deployment already did, newest first.

    Same contract as Office365's: one failing undo never stops the rest, and the failures are
    reported so the operator knows what is left over. A rollback never removes infrastructure the run
    *reused* rather than created.
    """

    def __init__(self):
        self._steps: List[tuple] = []

    def add(self, description: str, undo) -> None:
        self._steps.append((description, undo))

    async def run(self) -> List[str]:
        failures = []
        for description, undo in reversed(self._steps):
            try:
                logger.info(f"Rolling back: {description}")
                await undo()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Could not roll back {description}: {exc}")
                failures.append(f"{description} ({getattr(exc, 'detail', None) or exc})")
        return failures


async def provision_aws(
    customer_code: str,
    provision_aws_auth_keys: ProvisionAwsAuthKeys,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> ProvisionAwsResponse:
    """
    Deploy (or re-sync) one AWS instance of a customer.

    Order matters: everything that can be checked is checked before anything changes — the auth
    keys, the account's ownership, and the credentials against AWS itself. Then the manager, Graylog,
    Grafana, and finally CoPilot's own records; any failure on the way rolls back what this run did.
    """
    keys = provision_aws_auth_keys
    services = keys.service_configs()
    wanted = {config.key for config in services}
    logger.info(
        f"Provisioning AWS for customer {customer_code} (instance: {instance_name or 'default'}, account {keys.AWS_ACCOUNT_ID}, "
        f"services {sorted(wanted)}).",
    )

    await ensure_account_is_free(customer_code, instance_name, keys, session)

    try:
        validation = await validate_aws_access(keys, services)
    except AwsValidationError as e:
        raise HTTPException(status_code=400, detail=f"AWS validation failed, nothing was changed: {e}")

    customer_metas = await get_customer_aws_metas(customer_code, session)
    own_meta = next((meta for meta in customer_metas if meta.instance_name == instance_name), None)
    sibling_metas = [meta for meta in customer_metas if meta is not own_meta]

    own_streams = decode_service_ids(own_meta.graylog_stream_id) if own_meta else {}
    shared_index_sets: Dict[str, str] = {}
    shared_datasources: Dict[str, str] = {}
    for meta in customer_metas:
        for service, index_id in decode_service_ids(meta.graylog_index_id).items():
            shared_index_sets.setdefault(service, index_id)
        for service, uid in decode_service_ids(meta.grafana_datasource_uid).items():
            shared_datasources.setdefault(service, uid)
    shared_folder = next((meta.grafana_dashboard_folder_id for meta in customer_metas if meta.grafana_dashboard_folder_id), None)

    rollback = _ProvisioningRollback()
    warnings: List[str] = list(validation.warnings)
    restarted = False

    try:
        markers = await log_markers()

        # Wazuh master: this instance's buckets in the aws-s3 wodle.
        reconcile = await apply_instance_buckets(
            desired_buckets(keys),
            keys.BUCKET_NAME,
            keys.AWS_ACCOUNT_ID,
            adopt_existing=own_meta is not None,
            keep_only_logs_after=keys.ONLY_LOGS_AFTER is None,
        )
        if reconcile.changed:
            restarted = True
            previous = reconcile.previous
            rollback.add(
                f"the aws-s3 buckets for {keys.BUCKET_NAME} / account {keys.AWS_ACCOUNT_ID}",
                lambda: apply_instance_buckets(
                    previous,
                    keys.BUCKET_NAME,
                    keys.AWS_ACCOUNT_ID,
                    adopt_existing=True,
                    keep_only_logs_after=False,
                ),
            )
        if reconcile.wodle_disabled:
            warnings.append(
                "The aws-s3 wodle on the Wazuh manager is disabled (<disabled>yes</disabled>). CoPilot left that setting "
                "alone, so nothing is collected until it is enabled in ossec.conf.",
            )

        # Graylog: rules and pipeline, then per service an index set (shared) and a stream (this instance).
        await ensure_pipeline_rules()
        pipeline_id = await ensure_pipeline()

        index_ids: Dict[str, str] = {}
        stream_ids: Dict[str, str] = {}
        for config in services:
            definition = config.definition

            index_id = shared_index_sets.get(definition.key)
            if index_id:
                logger.info(f"Reusing this customer's AWS {definition.title} index set: {index_id}")
            else:
                index_id = await create_index_set(customer_code, definition, session)
                rollback.add(f"Graylog index set {index_id}", lambda index_id=index_id: delete_index_by_id(index_id=index_id))
            index_ids[definition.key] = index_id

            stream_id = own_streams.get(definition.key)
            if stream_id:
                logger.info(f"Keeping this instance's AWS {definition.title} stream: {stream_id}")
            else:
                stream_id = await create_event_stream(customer_code, definition, keys, index_id, session, instance_name=instance_name)
                rollback.add(f"Graylog stream {stream_id}", lambda stream_id=stream_id: delete_stream(stream_id=stream_id))
                await connect_and_start_stream(stream_id, pipeline_id)
            stream_ids[definition.key] = stream_id

        # Grafana: one folder per customer, one datasource per customer and service. No dashboards
        # exist for AWS yet, so none are provisioned.
        grafana_org_id = (await get_customer_meta(customer_code, session)).customer_meta.customer_meta_grafana_org_id

        folder_id = shared_folder
        if folder_id:
            logger.info(f"Reusing this customer's AWS Grafana folder {folder_id}.")
        else:
            folder_id = str((await create_grafana_folder(organization_id=grafana_org_id, folder_title=GRAFANA_FOLDER_TITLE)).id)
            rollback.add(f"Grafana folder {folder_id}", lambda: delete_folder(grafana_org_id, folder_id))

        datasource_uids: Dict[str, str] = {}
        for config in services:
            definition = config.definition
            uid = shared_datasources.get(definition.key)
            if not uid:
                uid = await create_grafana_datasource(customer_code, definition, grafana_org_id, session)
                rollback.add(
                    f"Grafana datasource {uid}",
                    lambda uid=uid: delete_grafana_datasource(organization_id=grafana_org_id, datasource_uid=uid),
                )
            datasource_uids[definition.key] = uid

        # The metadata is written *before* the integration is flagged as deployed: the UI hides the
        # Deploy button once `deployed` is true, so a failure in between would leave the
        # infrastructure untracked.
        await save_aws_meta(
            session,
            customer_code=customer_code,
            instance_name=instance_name,
            index_ids=index_ids,
            stream_ids=stream_ids,
            grafana_org_id=grafana_org_id,
            folder_id=folder_id,
            datasource_uids=datasource_uids,
        )
        await update_customer_integration_table(customer_code, session, instance_name=instance_name)

    except Exception as exc:
        logger.error(f"AWS provisioning failed for customer {customer_code}: {getattr(exc, 'detail', None) or exc}. Rolling back.")
        failures = await rollback.run()

        detail = getattr(exc, "detail", None) or str(exc)
        message = f"AWS deployment failed and was rolled back: {detail}"
        if failures:
            message += " Some resources could not be removed automatically: " + "; ".join(failures) + "."
        raise HTTPException(status_code=getattr(exc, "status_code", 500), detail=message)

    # Services dropped from SERVICES on a re-sync. Their buckets already left the manager above;
    # the Graylog and Grafana side is removed only now, after the new state is recorded, because
    # these deletions cannot be undone by a rollback.
    removed = sorted(set(own_streams) - wanted)
    if removed:
        still_used = {service for meta in sibling_metas for service in decode_service_ids(meta.graylog_stream_id)}
        own_index_sets = decode_service_ids(own_meta.graylog_index_id)
        own_datasources = decode_service_ids(own_meta.grafana_datasource_uid)
        warnings.extend(
            await remove_service_resources(
                removed,
                stream_ids=own_streams,
                index_ids=own_index_sets,
                datasource_uids=own_datasources,
                grafana_org_id=own_meta.grafana_org_id,
                keep_shared=still_used,
            ),
        )

    detected = await wait_for_profile_error(markers) if restarted else False

    return ProvisionAwsResponse(
        success=True,
        message=(
            f"Successfully provisioned AWS {', '.join(sorted(wanted))} for customer {customer_code}"
            + (f" (instance {instance_name})." if instance_name else ".")
        ),
        warnings=warnings,
        aws_config=aws_config_notice(detected, validation.bucket_region),
    )


######### ! Update Database ! ############


async def get_customer_aws_metas(customer_code: str, session: AsyncSession) -> List[CustomerIntegrationsMeta]:
    """Every AWS instance's metadata row for a customer — the source of what is shared between them."""
    result = await session.execute(
        select(CustomerIntegrationsMeta).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == AWS_INTEGRATION_NAME,
        ),
    )
    return list(result.scalars().all())


async def save_aws_meta(
    session: AsyncSession,
    customer_code: str,
    instance_name: Optional[str],
    index_ids: Dict[str, str],
    stream_ids: Dict[str, str],
    grafana_org_id: str,
    folder_id: str,
    datasource_uids: Dict[str, str],
) -> None:
    """Create or update the instance's metadata row; the per-service IDs are encoded as `service:id` pairs."""
    instance_clause = (
        CustomerIntegrationsMeta.instance_name.is_(None)
        if instance_name is None
        else CustomerIntegrationsMeta.instance_name == instance_name
    )
    result = await session.execute(
        select(CustomerIntegrationsMeta).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == AWS_INTEGRATION_NAME,
            instance_clause,
        ),
    )
    meta = result.scalars().first()
    if meta is None:
        meta = CustomerIntegrationsMeta(customer_code=customer_code, integration_name=AWS_INTEGRATION_NAME, instance_name=instance_name)
        session.add(meta)

    meta.graylog_input_id = None
    meta.graylog_index_id = encode_service_ids(index_ids)
    meta.graylog_stream_id = encode_service_ids(stream_ids)
    meta.grafana_org_id = str(grafana_org_id)
    meta.grafana_dashboard_folder_id = str(folder_id)
    meta.grafana_datasource_uid = encode_service_ids(datasource_uids)
    await session.commit()
    logger.info(f"AWS integration meta saved for customer {customer_code} (instance: {instance_name or 'default'}).")


async def update_customer_integration_table(
    customer_code: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> None:
    """Flag one AWS instance as deployed, leaving the customer's other instances as they are."""
    instance_clause = (
        CustomerIntegrations.instance_name.is_(None) if instance_name is None else CustomerIntegrations.instance_name == instance_name
    )
    await session.execute(
        update(CustomerIntegrations)
        .where(
            and_(
                CustomerIntegrations.customer_code == customer_code,
                CustomerIntegrations.integration_service_name == AWS_INTEGRATION_NAME,
                instance_clause,
            ),
        )
        .values(deployed=True),
    )
    await session.commit()
