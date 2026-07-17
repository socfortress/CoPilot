import re
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.incidents.models import FieldName
from app.incidents.models import AssetFieldName
from app.incidents.models import TimestampFieldName
from app.incidents.models import AlertTitleFieldName
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)

WAZUH_INDEX_PREFIX = "wazuh-alerts-4.x*"

# Default field mappings for Wazuh alerts (flat field names after flattening)
WAZUH_ASSET_FIELD = "agent_name"
WAZUH_TIMEFIELD = "@timestamp"
WAZUH_ALERT_TITLE_FIELD = "rule_description"
WAZUH_IOC_FIELDS = [
    "data_aws_sourceIPAddress",
    "data_aws_source_ip_address",
    "data_aws_userAgent",
    "data_aws_userIdentity_arn",
    "data_aws_userIdentity_accountId",
]

# Fields to include in alert context (supports * wildcard prefix)
WAZUH_CONTEXT_INCLUDE_PREFIXES = [
    "rule.",
    "agent.",
    "manager.",
    "cluster.",
    "data.",
    "decoder.",
    "input.",
    "full_log",
    "location",
    "id",
    "GeoLocation.",
]


async def get_wazuh_alert_indices() -> List[str]:
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        indices = await es_client.indices.get_alias(WAZUH_INDEX_PREFIX)
        return sorted(list(indices.keys()))
    except Exception as e:
        logger.warning(f"Failed to get Wazuh alert indices: {e}")
        return []


async def get_unprocessed_wazuh_alerts(
    batch_size: int = 100,
    excluded_ids: Optional[set] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    indices = await get_wazuh_alert_indices()
    if not indices:
        logger.info("No Wazuh alert indices found")
        return [], 0

    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

    query = {
        "query": {
            "bool": {
                "must_not": [{"exists": {"field": "copilot_alert_id"}}],
            },
        },
        "sort": [{"@timestamp": {"order": "asc"}}],
    }

    alerts: List[Dict[str, Any]] = []
    total_remaining = 0
    excluded_ids_set = excluded_ids or set()

    for index in indices:
        if len(alerts) >= batch_size:
            break

        try:
            remaining = batch_size - len(alerts)
            response = await es_client.search(
                index=index,
                body=query,
                size=remaining,
            )

            hits = response["hits"]["hits"]
            total = (
                response["hits"]["total"]["value"]
                if isinstance(response["hits"]["total"], dict)
                else response["hits"]["total"]
            )

            for hit in hits:
                doc_id = hit["_id"]
                if doc_id not in excluded_ids_set:
                    alerts.append(hit)
                    excluded_ids_set.add(doc_id)

            total_remaining += total
            logger.info(
                f"Found {len(hits)} unprocessed alerts in {index} (total matching: {total})",
            )
        except Exception as e:
            logger.warning(f"Error querying index {index}: {e}")
            continue

    return alerts, total_remaining


def flatten_source(source: Dict[str, Any]) -> Dict[str, Any]:
    flat = {}
    for key, value in source.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}_{sub_key}"] = sub_value
        else:
            flat[key] = value
    return flat


async def ensure_wazuh_field_names(session: AsyncSession):
    source = "wazuh"

    existing = await session.execute(
        select(FieldName).where(FieldName.source == source).limit(1),
    )
    if existing.scalars().first():
        return

    asset = await session.execute(
        select(AssetFieldName).where(AssetFieldName.source == source).limit(1),
    )
    if asset.scalars().first():
        return

    logger.info("Seeding Wazuh field name mappings...")

    # Context fields (flattened names)
    context_fields = [
        "agent_id",
        "agent_name",
        "manager_name",
        "cluster_name",
        "cluster_node",
        "decoder_name",
        "rule_firedtimes",
        "rule_mail",
        "rule_level",
        "rule_description",
        "rule_groups",
        "rule_id",
        "full_log",
        "input_type",
        "location",
        "id",
    ]
    for field in context_fields:
        session.add(FieldName(source=source, field_name=field))

    session.add(AssetFieldName(source=source, field_name=WAZUH_ASSET_FIELD))
    session.add(TimestampFieldName(source=source, field_name=WAZUH_TIMEFIELD))
    session.add(AlertTitleFieldName(source=source, field_name=WAZUH_ALERT_TITLE_FIELD))
    await session.commit()
    logger.info("Wazuh field name mappings seeded.")


def build_wazuh_alert_payload(hit: Dict[str, Any]) -> CreatedAlertPayload:
    source = hit["_source"]
    flat = flatten_source(source)

    title = flat.get("rule_description") or flat.get("rule.description") or "Wazuh Alert"
    timestamp = flat.get("@timestamp") or flat.get("timestamp") or datetime.utcnow().isoformat()
    asset_name = flat.get("agent_name") or flat.get("agent.name") or "unknown"

    context = {"raw_alert": source}
    return CreatedAlertPayload(
        alert_context_payload=context,
        asset_payload=str(asset_name),
        timefield_payload=str(timestamp),
        alert_title_payload=str(title),
        source="wazuh",
        index_name=hit["_index"],
        index_id=hit["_id"],
    )


async def get_wazuh_customer_code(
    hit: Dict[str, Any],
    session: AsyncSession,
) -> str:
    source = hit["_source"]
    flat = flatten_source(source)

    # Check if any field matches a known customer code in alert_creation_settings
    result = await session.execute(select(AlertCreationSettings))
    settings = result.scalars().all()

    if settings:
        matched = None
        for setting in settings:
            code = setting.customer_code
            for value in flat.values():
                if isinstance(value, str) and (
                    code.lower() in value.lower() or value.lower() in code.lower()
                ):
                    matched = code
                    break
            if matched:
                break
        if matched:
            return matched

        return settings[0].customer_code

    return "wazuh"


async def stamp_wazuh_alert(index: str, alert_id: str, copilot_alert_id: int):
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    body = {"doc": {"copilot_alert_id": str(copilot_alert_id)}}
    try:
        await es_client.update(index=index, id=alert_id, body=body)
        logger.info(
            f"Stamped copilot_alert_id {copilot_alert_id} on Wazuh alert {alert_id} in {index}",
        )
    except Exception as e:
        logger.warning(f"Failed to stamp copilot_alert_id on {index}/{alert_id}: {e}")


async def ingest_wazuh_alerts(
    session: AsyncSession,
    batch_size: int = 100,
    max_batches: int = 10,
) -> Dict[str, int]:
    from app.incidents.services.incident_alert import create_alert_full

    await ensure_wazuh_field_names(session)

    total_created = 0
    total_failed = 0
    batches_processed = 0
    excluded_ids: set = set()

    for batch_num in range(max_batches):
        alerts, total_remaining = await get_unprocessed_wazuh_alerts(
            batch_size=batch_size,
            excluded_ids=excluded_ids,
        )

        if not alerts:
            break

        logger.info(
            f"Processing batch {batch_num + 1}: {len(alerts)} Wazuh alerts "
            f"(total remaining: {total_remaining})",
        )

        batch_created = 0
        batch_failed = 0

        for hit in alerts:
            try:
                payload = build_wazuh_alert_payload(hit)
                customer_code = await get_wazuh_customer_code(hit, session)

                alert_id = await create_alert_full(
                    alert_payload=payload,
                    customer_code=customer_code,
                    session=session,
                )

                await stamp_wazuh_alert(hit["_index"], hit["_id"], alert_id)
                batch_created += 1
                total_created += 1

            except Exception as e:
                logger.opt(exception=True).error(
                    f"Failed to ingest Wazuh alert {hit.get('_id', 'unknown')}: {e}",
                )
                batch_failed += 1
                total_failed += 1

        batches_processed += 1
        logger.info(
            f"Batch {batch_num + 1} complete: {batch_created} created, {batch_failed} failed",
        )

        if len(alerts) < batch_size:
            break

    return {
        "created": total_created,
        "failed": total_failed,
        "batches": batches_processed,
    }
