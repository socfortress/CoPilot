"""
Set SOCFortress UBA up for a customer: ``POST /api/uba/{customer_code}/provision``.

UBA decides *what* to create (``GET /v1/provisioning``: object names, where Graylog
reaches UBA's GELF receiver, where the UBA ALERTS input listens, the routing rules
per source, the Wazuh rules it relies on); CoPilot creates it next to the streams
customer provisioning and Office365 provisioning already made:

1. Register the customer with UBA (``PUT /v1/tenants/{code}``) with its Microsoft
   365 tenant ids and, when they differ from UBA's defaults, its index patterns.
   UBA's worker then replays ``bootstrap_days`` of history (alerting off) and goes
   live. Registering comes first: events reaching UBA before it would be processed
   without a bootstrap.
2. Per source (the customer's Wazuh stream; its Office365 streams, if any): a
   "UBA FEED" stream in the source stream's index set (so routed messages are not
   indexed twice), the routing rules, and a "UBA ROUTING" pipeline connected to the
   source stream(s) only.
3. One GELF output to UBA, attached to the feed streams.
4. The way back: the global "UBA ALERTS" GELF input (once per Graylog) and a
   "UBA ALERTS - <code>" stream in the Wazuh index set. No pipeline may be connected
   to it: UBA never consumes its own output.
5. Optional: the Wazuh rules UBA relies on (4723/4724), uploaded to the manager,
   which is then restarted.

Every step looks the object up by title first, so running it again repairs a
partial setup instead of duplicating anything.
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_post_request_create_entity
from app.connectors.graylog.utils.universal import send_put_request
from app.connectors.uba.schema.provision import UbaProvisionRequest
from app.connectors.uba.schema.provision import UbaProvisionResponse
from app.connectors.uba.schema.provision import UbaProvisionStatusResponse
from app.connectors.uba.schema.provision import UbaProvisionStep
from app.connectors.uba.schema.provision import UbaSourceStream
from app.connectors.uba.utils.universal import UbaRequestError
from app.connectors.uba.utils.universal import path_segment
from app.connectors.uba.utils.universal import uba_request
from app.db.universal_models import CustomersMeta
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrationsMeta,
)
from app.integrations.models.customer_integration_settings import IntegrationAuthKeys
from app.integrations.models.customer_integration_settings import IntegrationService
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)

GELF_OUTPUT = "org.graylog2.outputs.GelfOutput"
GELF_TCP_INPUT = "org.graylog2.inputs.gelf.tcp.GELFTCPInput"
# UBA's own default index patterns: sent to UBA only when the customer's index sets differ.
DEFAULT_INDEX = {"wazuh": "wazuh-{code}_*", "office365": "office365-{code}_*,graylog_*"}


class _Steps:
    def __init__(self) -> None:
        self.items: List[UbaProvisionStep] = []

    def add(self, step: str, status: str, detail: str = "") -> None:
        logger.info(f"UBA provisioning: {step}: {status} {detail}".rstrip())
        self.items.append(UbaProvisionStep(step=step, status=status, detail=detail))


# -- what the customer already has ----------------------------------------------------------------


async def _index_prefix(index_set_id: str) -> str:
    response = await send_get_request(endpoint=f"/api/system/indices/index_sets/{index_set_id}")
    prefix = (response.get("data") or {}).get("index_prefix")
    if not prefix:
        raise HTTPException(status_code=502, detail=f"Graylog index set {index_set_id} has no index prefix")
    return prefix


async def _office365_tenant_ids(customer_code: str, session: AsyncSession) -> List[str]:
    """Every Microsoft 365 tenant provisioned for the customer (the TENANT_ID auth key per instance)."""
    result = await session.execute(
        select(IntegrationAuthKeys.auth_value)
        .join(IntegrationSubscription, IntegrationAuthKeys.subscription_id == IntegrationSubscription.id)
        .join(IntegrationService, IntegrationSubscription.integration_service_id == IntegrationService.id)
        .join(CustomerIntegrations, CustomerIntegrations.id == IntegrationSubscription.customer_id)
        .where(
            CustomerIntegrations.customer_code == customer_code,
            IntegrationService.service_name == "Office365",
            IntegrationAuthKeys.auth_key_name == "TENANT_ID",
        ),
    )
    return sorted({str(v).strip().lower() for v in result.scalars().all() if v and str(v).strip()})


async def _customer_meta(customer_code: str, session: AsyncSession) -> Optional[CustomersMeta]:
    result = await session.execute(select(CustomersMeta).where(CustomersMeta.customer_code == customer_code))
    return result.scalars().first()


async def _source_streams(customer_code: str, session: AsyncSession) -> Dict[str, List[UbaSourceStream]]:
    """The streams UBA reads from, per UBA source name (WAZUH, O365)."""
    customer_meta = await _customer_meta(customer_code, session)
    if customer_meta is None or not customer_meta.customer_meta_graylog_stream:
        raise HTTPException(
            status_code=409,
            detail=f"Customer {customer_code} has no Wazuh stream on record: provision the customer first",
        )
    sources = {
        "WAZUH": [
            UbaSourceStream(
                stream_id=customer_meta.customer_meta_graylog_stream,
                index_set_id=customer_meta.customer_meta_graylog_index,
            ),
        ],
    }
    rows = await session.execute(
        select(CustomerIntegrationsMeta).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == "Office365",
        ),
    )
    o365 = [
        UbaSourceStream(stream_id=r.graylog_stream_id, index_set_id=r.graylog_index_id, instance=r.instance_name)
        for r in rows.scalars().all()
        if r.graylog_stream_id
    ]
    if o365:
        sources["O365"] = o365
    return sources


# -- Graylog objects --------------------------------------------------------------------------------


async def _list(endpoint: str, key: Optional[str] = None) -> List[Dict[str, Any]]:
    data = (await send_get_request(endpoint=endpoint)).get("data")
    return (data or {}).get(key, []) if key else (data or [])


async def _feed_stream(title: str, source: UbaSourceStream, streams: Dict[str, Dict], steps: _Steps) -> str:
    existing = streams.get(title)
    if existing is not None:
        if existing.get("index_set_id") != source.index_set_id:
            raise HTTPException(
                status_code=409,
                detail=f"Stream {title} writes to another index set than its source stream: messages would be indexed twice",
            )
        steps.add(f"stream {title}", "exists")
        return existing["id"]
    created = await send_post_request_create_entity(
        endpoint="/api/streams",
        entity={
            "title": title,
            "description": "SOCFortress UBA feed: filled by its UBA ROUTING pipeline, sent to UBA by its output",
            "rules": [],
            "matching_type": "AND",
            "remove_matches_from_default_stream": True,
            "index_set_id": source.index_set_id,
        },
    )
    stream_id = created["data"]["stream_id"]
    await send_post_request(endpoint=f"/api/streams/{stream_id}/resume")
    steps.add(f"stream {title}", "created")
    return stream_id


def _rule_title(source: str) -> str:
    return source.split('"', 2)[1]


async def _routing(
    pipeline_title: str,
    stage: int,
    rule_sources: List[str],
    source_stream_ids: List[str],
    steps: _Steps,
) -> None:
    rules = {r["title"]: r for r in await _list("/api/system/pipelines/rule")}
    titles = []
    for text in rule_sources:
        title = _rule_title(text)
        titles.append(title)
        body = {"title": title, "description": "SOCFortress UBA routing", "source": text}
        if title in rules:
            if rules[title].get("source", "").strip() != text.strip():
                await send_put_request(endpoint=f"/api/system/pipelines/rule/{rules[title]['id']}", data=body)
                steps.add(f"rule {title}", "updated")
            else:
                steps.add(f"rule {title}", "exists")
        else:
            await send_post_request(endpoint="/api/system/pipelines/rule", data=body)
            steps.add(f"rule {title}", "created")

    source = f'pipeline "{pipeline_title}"\nstage {stage} match either\n'
    source += "".join(f'rule "{t}"\n' for t in titles) + "end"
    body = {"title": pipeline_title, "description": "SOCFortress UBA routing", "source": source}
    pipelines = {p["title"]: p for p in await _list("/api/system/pipelines/pipeline")}
    if pipeline_title in pipelines:
        pipeline_id = pipelines[pipeline_title]["id"]
        await send_put_request(endpoint=f"/api/system/pipelines/pipeline/{pipeline_id}", data=body)
        steps.add(f"pipeline {pipeline_title}", "updated")
    else:
        pipeline_id = (await send_post_request(endpoint="/api/system/pipelines/pipeline", data=body))["data"]["id"]
        steps.add(f"pipeline {pipeline_title}", "created")
    # to_pipeline sets this pipeline's streams (ours alone); to_stream would replace the source
    # stream's other pipelines (the Wazuh / Office365 processing pipelines).
    await send_post_request(
        endpoint="/api/system/pipelines/connections/to_pipeline",
        data={"pipeline_id": pipeline_id, "stream_ids": source_stream_ids},
    )
    steps.add(f"pipeline {pipeline_title}", "connected", f"to {len(source_stream_ids)} source stream(s)")


async def _output(title: str, host: str, port: int, feed_stream_ids: List[str], steps: _Steps) -> None:
    config = {
        "hostname": host,
        "port": port,
        "protocol": "TCP",
        "connect_timeout": 1000,
        "reconnect_delay": 500,
        "tcp_no_delay": False,
        "tcp_keep_alive": True,
        "tls_verification_enabled": False,
        "tls_trust_cert_chain": "",
        "queue_size": 512,
        "max_inflight_sends": 512,
    }
    outputs = {o["title"]: o for o in await _list("/api/system/outputs", "outputs")}
    if title in outputs:
        output_id = outputs[title]["id"]
        current = outputs[title].get("configuration") or {}
        if (current.get("hostname"), current.get("port")) != (host, port):
            await send_put_request(
                endpoint=f"/api/system/outputs/{output_id}",
                data={"title": title, "type": GELF_OUTPUT, "configuration": config},
            )
            steps.add(f"output {title}", "updated", f"-> {host}:{port}")
        else:
            steps.add(f"output {title}", "exists", f"-> {host}:{port}")
    else:
        created = await send_post_request(
            endpoint="/api/system/outputs",
            data={"title": title, "type": GELF_OUTPUT, "configuration": config, "streams": []},
        )
        output_id = created["data"]["id"]
        steps.add(f"output {title}", "created", f"-> {host}:{port}")
    for stream_id in feed_stream_ids:
        await send_post_request(endpoint=f"/api/streams/{stream_id}/outputs", data={"outputs": [output_id]})
    steps.add(f"output {title}", "attached", f"to {len(feed_stream_ids)} feed stream(s)")


async def _alerts(info: Dict[str, Any], customer_code: str, wazuh_index_set: str, steps: _Steps) -> None:
    names = info["graylog"]
    listen = info["alerts_input"]
    inputs = {i["title"]: i for i in await _list("/api/system/inputs", "inputs")}
    if names["alerts_input"] in inputs:
        attrs = inputs[names["alerts_input"]].get("attributes") or {}
        steps.add(f"input {names['alerts_input']}", "exists", f"{attrs.get('bind_address')}:{attrs.get('port')}")
    else:
        await send_post_request(
            endpoint="/api/system/inputs",
            data={
                "title": names["alerts_input"],
                "type": GELF_TCP_INPUT,
                "global": True,
                "configuration": {
                    "bind_address": listen["bind_address"],
                    "port": listen["port"],
                    "use_null_delimiter": True,
                    "max_message_size": 2097152,
                    "recv_buffer_size": 1048576,
                    "number_worker_threads": 2,
                    "tcp_keepalive": True,
                    "tls_enable": False,
                    "charset_name": "UTF-8",
                    "decompress_size_limit": 8388608,
                },
            },
        )
        steps.add(f"input {names['alerts_input']}", "created", f"{listen['bind_address']}:{listen['port']}")

    title = names["alerts_stream"].format(tenant=customer_code)
    streams = {s["title"]: s for s in await _list("/api/streams", "streams")}
    if title in streams:
        steps.add(f"stream {title}", "exists")
        return
    rules = [
        {"field": field, "type": 1, "value": value.format(tenant=customer_code), "inverted": False, "description": "UBA"}
        for field, value in names["alerts_stream_rules"].items()
    ]
    created = await send_post_request_create_entity(
        endpoint="/api/streams",
        entity={
            "title": title,
            "description": "SOCFortress UBA alerts (no UBA pipeline may be connected: loop guard)",
            "rules": rules,
            "matching_type": "AND",
            "remove_matches_from_default_stream": True,
            "index_set_id": wazuh_index_set,
        },
    )
    stream_id = created["data"]["stream_id"]
    await send_post_request(endpoint=f"/api/streams/{stream_id}/resume")
    steps.add(f"stream {title}", "created", "in the Wazuh index set")


async def _wazuh_rules(files: List[Dict[str, str]], steps: _Steps) -> None:
    from app.connectors.wazuh_manager.services.rules import update_wazuh_rule_file
    from app.connectors.wazuh_manager.utils.universal import (
        send_put_request as wazuh_put,
    )

    for f in files:
        await update_wazuh_rule_file(f["filename"], f["content"].encode(), overwrite=True)
        steps.add(f"Wazuh rules {f['filename']}", "uploaded")
    if files:
        await wazuh_put(endpoint="/manager/restart", data=None)
        steps.add(
            "Wazuh manager",
            "restarted",
            "check that the log shipper (e.g. Fluent Bit) still ships alerts.json after the restart",
        )


# -- entry points -----------------------------------------------------------------------------------


async def _provisioning_info() -> Dict[str, Any]:
    info = await uba_request("GET", "/v1/provisioning")
    missing = [
        name
        for name, value in (
            ("UBA_PROVISION_FEED_HOST", info.get("feed_output")),
            ("UBA_PROVISION_ALERTS_BIND", info.get("alerts_input")),
        )
        if not value
    ]
    if missing:
        raise UbaRequestError(
            "not_configured",
            f"SOCFortress UBA does not say where Graylog reaches it: set {' and '.join(missing)} in UBA's environment",
            409,
        )
    return info


async def get_provisioning_status(customer_code: str, session: AsyncSession) -> UbaProvisionStatusResponse:
    """What UBA provisioning would use, and the customer's state in UBA (onboarding progress)."""
    try:
        sources = await _source_streams(customer_code, session)
        problem = None
    except HTTPException as e:
        sources, problem = {}, e.detail
    try:
        onboarding = await uba_request("GET", f"/v1/tenants/{path_segment(customer_code)}/onboarding")
    except UbaRequestError as e:
        if e.status_code != 404:
            raise
        onboarding = None
    return UbaProvisionStatusResponse(
        success=True,
        message="UBA is set up for this customer" if onboarding and onboarding.get("active") else "UBA is not set up",
        sources={k: len(v) for k, v in sources.items()},
        office365_tenants=await _office365_tenant_ids(customer_code, session),
        problem=problem,
        onboarding=onboarding,
    )


async def provision_uba(customer_code: str, request: UbaProvisionRequest, session: AsyncSession) -> UbaProvisionResponse:
    steps = _Steps()
    info = await _provisioning_info()
    names = info["graylog"]
    sources = await _source_streams(customer_code, session)
    tenant_ids = await _office365_tenant_ids(customer_code, session)
    meta = await _customer_meta(customer_code, session)

    # 1. Register with UBA first (see the module docstring).
    indices: Dict[str, str] = {}
    for name, streams in sources.items():
        integration = names["sources"][name]
        prefix = await _index_prefix(streams[0].index_set_id)
        default = DEFAULT_INDEX[integration].format(code=customer_code.lower())
        if not default.startswith(f"{prefix}_*"):
            indices[integration] = f"{prefix}_*"
    registration = await uba_request(
        "PUT",
        f"/v1/tenants/{path_segment(customer_code)}",
        json={
            "name": meta.customer_name,
            "active": True,
            "bootstrap_days": request.bootstrap_days,
            "office365_organization_ids": tenant_ids,
            "indices": indices or None,
        },
    )
    steps.add(
        "UBA tenant",
        "registered",
        f"{registration.get('status')}; {len(tenant_ids)} Microsoft 365 tenant(s); {request.bootstrap_days} day(s) of history",
    )

    # 2-3. Feed streams, routing, output.
    streams = {s["title"]: s for s in await _list("/api/streams", "streams")}
    feed_ids = []
    for name, source_streams in sources.items():
        integration = names["sources"][name]
        title = names["feed_stream"].format(source=name, tenant=customer_code)
        feed_ids.append(await _feed_stream(title, source_streams[0], streams, steps))
        rule_sources = (await uba_request("GET", f"/v1/integrations/{integration}/graylog-rules", params={"stream": title}))["rules"]
        await _routing(
            names["routing_pipeline"].format(source=name, tenant=customer_code),
            names["pipeline_stage"],
            rule_sources,
            [s.stream_id for s in source_streams],
            steps,
        )
    output = info["feed_output"]
    await _output(names["output"].format(tenant=customer_code), output["host"], output["port"], feed_ids, steps)

    # 4. Alerts back into Graylog.
    await _alerts(info, customer_code, meta.customer_meta_graylog_index, steps)

    # 5. Optional Wazuh rules.
    if request.deploy_wazuh_rules:
        await _wazuh_rules(info.get("wazuh_rules") or [], steps)
    else:
        steps.add("Wazuh rules", "skipped", "not requested")

    return UbaProvisionResponse(
        success=True,
        message=f"UBA is set up for {customer_code}: it replays history, then goes live",
        steps=steps.items,
        onboarding=registration,
    )
