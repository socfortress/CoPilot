"""Roll SOCFortress UBA back for one customer (#1241): ``GET|POST /api/uba/{customer_code}/rollback``.

UBA is optional; the customer's Wazuh and Office365 processing is not. Rollback removes
what UBA setup (``services/provision.py``) put next to the customer's streams, and only
that, in an order that never leaves Graylog routing to something that is gone:

1. Disconnect each UBA ROUTING pipeline from the customer's source streams. From here on
   nothing reaches the feed streams, so nothing reaches the GELF output to UBA either: an
   unreachable UBA can no longer back Graylog's output buffer up.
2. Detach the "UBA GELF" output from the feed streams and delete it.
3. Delete the routing pipelines, then their rules (a rule is deleted once no pipeline
   runs it).
4. Delete the feed streams. A feed stream sits in its source stream's index set, so its
   messages were indexed once, with the source stream: nothing indexed is lost.
5. Delete the customer's UBA ALERTS stream (its alerts stay in the index), and the shared
   "UBA ALERTS" input once no other customer has a UBA alerts stream.
6. Deactivate the customer in UBA (``active: false``). UBA keeps its entities, alerts,
   verdicts and suppressions; CoPilot keeps its incident alerts.
7. Check that the customer's source streams still run with their other pipelines, and
   that Graylog's event definitions are unchanged.

What the customer owns comes from ``uba_provisioned_resource`` (setup records every
object), plus objects with setup's titles for customers set up before that table. Either
way an object is only removed when it still looks like what setup makes (a feed stream
with no stream rules, a pipeline that runs only the customer's UBA routing rules, ...)
and nothing else uses it (another pipeline, an event definition, another output);
anything else is reported as a conflict and left alone. The Wazuh rules UBA relies on are
never removed: they are shared, and removing them means restarting the Wazuh manager.

Every step is idempotent and a failed step does not stop the independent ones, so running
the rollback again finishes it. The report (snapshot, steps, checks) is kept in
``uba_rollback``. Setting UBA up again recreates everything.
"""

import re
from dataclasses import dataclass
from dataclasses import field
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.graylog.utils.universal import send_delete_request
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.uba.schema.provision import UbaProvisionStep
from app.connectors.uba.schema.provision import UbaRollbackCheck
from app.connectors.uba.schema.provision import UbaRollbackItem
from app.connectors.uba.schema.provision import UbaRollbackPlan
from app.connectors.uba.schema.provision import UbaRollbackReport
from app.connectors.uba.services import ownership
from app.connectors.uba.services.ownership import Owned
from app.connectors.uba.services.provision import GELF_OUTPUT
from app.connectors.uba.services.provision import GELF_TCP_INPUT
from app.connectors.uba.utils.universal import UbaRequestError
from app.connectors.uba.utils.universal import path_segment
from app.connectors.uba.utils.universal import uba_request
from app.db.universal_models import CustomersMeta
from app.db.universal_models import UbaRollback
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrationsMeta,
)
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

# UBA's object names (GET /v1/provisioning "graylog"), used when UBA cannot be asked: a rollback
# must work while UBA is down, which is when it is needed most.
DEFAULT_NAMES = {
    "sources": {"WAZUH": "wazuh", "O365": "office365"},
    "feed_stream": "UBA FEED - {source} - {tenant}",
    "routing_pipeline": "UBA ROUTING - {source} - {tenant}",
    "output": "UBA GELF - {tenant}",
    "alerts_input": "UBA ALERTS",
    "alerts_stream": "UBA ALERTS - {tenant}",
}
RUNNING_FOR = timedelta(minutes=10)  # a rollback "running" for longer died with its process

_RULE_IN_PIPELINE = re.compile(r'^\s*rule\s+"([^"]+)"', re.MULTILINE)
_ROUTE_TO = re.compile(r'route_to_stream\s*\(\s*name\s*:\s*"([^"]+)"')


# -- what Graylog holds ----------------------------------------------------------------------------


@dataclass
class GraylogState:
    streams: Dict[str, Dict[str, Any]]
    pipelines: Dict[str, Dict[str, Any]]
    rules: Dict[str, Dict[str, Any]]
    outputs: Dict[str, Dict[str, Any]]
    inputs: Dict[str, Dict[str, Any]]
    connections: Dict[str, List[str]]  # stream id -> pipeline ids
    event_definitions: Optional[List[Dict[str, Any]]]  # None: could not be read

    def pipeline_rules(self, pipeline_id: str) -> List[str]:
        pipeline = self.pipelines.get(pipeline_id) or {}
        titles = [r for stage in pipeline.get("stages") or [] for r in stage.get("rules") or []]
        return titles or _RULE_IN_PIPELINE.findall(pipeline.get("source") or "")

    def pipeline_streams(self, pipeline_id: str) -> List[str]:
        return sorted(s for s, pipelines in self.connections.items() if pipeline_id in pipelines)

    def stream_outputs(self, stream_id: str) -> List[str]:
        return [o["id"] if isinstance(o, dict) else str(o) for o in (self.streams.get(stream_id) or {}).get("outputs") or []]

    def output_streams(self, output_id: str) -> List[str]:
        return sorted(s for s in self.streams if output_id in self.stream_outputs(s))

    def definitions_on(self, stream_id: str) -> List[Dict[str, Any]]:
        return [d for d in self.event_definitions or [] if stream_id in ((d.get("config") or {}).get("streams") or [])]


async def _get(endpoint: str, key: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Any:
    data = (await send_get_request(endpoint=endpoint, params=params)).get("data")
    return (data or {}).get(key, []) if key else (data or [])


async def _event_definitions() -> Optional[List[Dict[str, Any]]]:
    try:
        found: List[Dict[str, Any]] = []
        page = 1
        while True:
            data = await _get("/api/events/definitions", params={"per_page": 500, "page": page})
            batch = (data or {}).get("event_definitions") or []
            found.extend(batch)
            total = (data or {}).get("total")
            if not batch or (total is not None and len(found) >= total) or page >= 50:
                return found
            page += 1
    except HTTPException as e:
        logger.warning(f"UBA rollback: could not read Graylog's event definitions: {e.detail}")
        return None


async def read_graylog() -> GraylogState:
    connections: Dict[str, List[str]] = {}
    for c in await _get("/api/system/pipelines/connections"):
        connections.setdefault(c["stream_id"], []).extend(c.get("pipeline_ids") or [])
    return GraylogState(
        streams={s["id"]: s for s in await _get("/api/streams", "streams")},
        pipelines={p["id"]: p for p in await _get("/api/system/pipelines/pipeline")},
        rules={r["id"]: r for r in await _get("/api/system/pipelines/rule")},
        outputs={o["id"]: o for o in await _get("/api/system/outputs", "outputs")},
        inputs={i["id"]: i for i in await _get("/api/system/inputs", "inputs")},
        connections=connections,
        event_definitions=await _event_definitions(),
    )


# -- what the customer owns ------------------------------------------------------------------------


async def _source_stream_ids(customer_code: str, session: AsyncSession) -> List[str]:
    """The customer's Wazuh and Office365 streams: never touched, whatever else holds."""
    ids: List[str] = []
    meta = (await session.execute(select(CustomersMeta).where(CustomersMeta.customer_code == customer_code))).scalars().first()
    if meta is not None and meta.customer_meta_graylog_stream:
        ids.append(meta.customer_meta_graylog_stream)
    rows = await session.execute(
        select(CustomerIntegrationsMeta.graylog_stream_id).where(
            CustomerIntegrationsMeta.customer_code == customer_code,
            CustomerIntegrationsMeta.integration_name == "Office365",
        ),
    )
    ids.extend(s for s in rows.scalars().all() if s and s not in ids)
    return ids


@dataclass
class Item:
    kind: str
    graylog_id: str
    title: str
    source: Optional[str] = None
    recorded: bool = False
    shared: bool = False
    detail: str = ""
    action: str = "remove"  # remove | keep | conflict

    def out(self) -> UbaRollbackItem:
        return UbaRollbackItem(
            kind=self.kind,
            id=self.graylog_id,
            title=self.title,
            source=self.source,
            recorded=self.recorded,
            detail=self.detail,
        )

    def owned(self) -> Owned:
        return Owned(self.kind, self.graylog_id, self.title, self.source, self.shared, "found" if self.recorded else "adopted")


@dataclass
class Plan:
    customer_code: str
    names: Dict[str, Any]
    state: GraylogState
    source_streams: List[str]
    items: List[Item] = field(default_factory=list)
    gone: List[Item] = field(default_factory=list)  # recorded, no longer in Graylog
    uba: Optional[Dict[str, Any]] = None
    uba_problem: Optional[str] = None

    def of(self, kind: str, action: Optional[str] = "remove") -> List[Item]:
        return [i for i in self.items if i.kind == kind and (action is None or i.action == action)]

    def feed_titles(self) -> Set[str]:
        return {i.title for i in self.of(ownership.FEED_STREAM, None)} | {
            self.names["feed_stream"].format(source=s, tenant=self.customer_code) for s in self.names["sources"]
        }


async def _names() -> Dict[str, Any]:
    """UBA's object names; setup's defaults when UBA cannot be asked (not an error here)."""
    try:
        info = await uba_request("GET", "/v1/provisioning")
        return {**DEFAULT_NAMES, **(info.get("graylog") or {})}
    except UbaRequestError as e:
        logger.info(f"UBA rollback: UBA's object names unavailable ({e.detail}); using setup's defaults")
        return dict(DEFAULT_NAMES)


async def _onboarding(customer_code: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        return await uba_request("GET", f"/v1/tenants/{path_segment(customer_code)}/onboarding"), None
    except UbaRequestError as e:
        if e.status_code == 404:
            return None, None
        return None, e.detail


def _candidates(
    plan: Plan,
    kind: str,
    recorded: Dict[str, List[Any]],
    objects: Dict[str, Dict[str, Any]],
    titles: Dict[str, Optional[str]],
) -> List[Item]:
    """Recorded objects of ``kind`` plus objects carrying one of ``titles`` (title -> source)."""
    found: Dict[str, Item] = {}
    for row in recorded.get(kind, []):
        obj = objects.get(row.graylog_id)
        if obj is None:
            plan.gone.append(Item(kind, row.graylog_id, row.title, row.source, recorded=True, shared=row.shared))
            continue
        found[row.graylog_id] = Item(kind, row.graylog_id, obj.get("title") or row.title, row.source, recorded=True, shared=row.shared)
    for object_id, obj in objects.items():
        if object_id not in found and obj.get("title") in titles:
            found[object_id] = Item(kind, object_id, obj["title"], titles[obj["title"]])
    return list(found.values())


def _conflict(item: Item, why: str) -> Item:
    item.action, item.detail = "conflict", why
    return item


async def build_plan(customer_code: str, session: AsyncSession) -> Plan:
    names = await _names()
    state = await read_graylog()
    plan = Plan(customer_code, names, state, await _source_stream_ids(customer_code, session))
    plan.uba, plan.uba_problem = await _onboarding(customer_code)
    recorded: Dict[str, List[Any]] = {}
    for row in await ownership.active(session, customer_code):
        recorded.setdefault(row.kind, []).append(row)
    code = customer_code
    sources = list(names["sources"])
    protected = set(plan.source_streams)

    # Feed streams.
    feed_titles = {names["feed_stream"].format(source=s, tenant=code): s for s in sources}
    for item in _candidates(plan, ownership.FEED_STREAM, recorded, state.streams, feed_titles):
        stream = state.streams[item.graylog_id]
        item.source = item.source or feed_titles.get(item.title)
        if item.graylog_id in protected or stream.get("is_default"):
            plan.items.append(_conflict(item, "is one of the customer's own streams"))
        elif not item.title.startswith("UBA FEED - ") or stream.get("rules"):
            plan.items.append(_conflict(item, "does not look like a UBA feed stream (renamed, or it has stream rules)"))
        else:
            plan.items.append(item)

    # Routing pipelines: only the customer's UBA routing rules may run in them.
    feeds = plan.feed_titles()
    pipeline_titles = {names["routing_pipeline"].format(source=s, tenant=code): s for s in sources}
    for item in _candidates(plan, ownership.ROUTING_PIPELINE, recorded, state.pipelines, pipeline_titles):
        item.source = item.source or pipeline_titles.get(item.title)
        foreign = [r for r in state.pipeline_rules(item.graylog_id) if not any(r.startswith(f"{t} - ") for t in feeds)]
        connected = state.pipeline_streams(item.graylog_id)
        if not item.title.startswith("UBA ROUTING - ") or foreign:
            plan.items.append(_conflict(item, f"runs rules UBA setup did not make: {', '.join(foreign[:5])}" if foreign else "renamed"))
        else:
            item.detail = f"connected to {len(connected)} stream(s)"
            plan.items.append(item)
    removable_pipelines = {i.graylog_id for i in plan.of(ownership.ROUTING_PIPELINE)}

    # Routing rules: route only to the customer's feed streams, run by no other pipeline.
    rule_titles = {r["title"]: None for r in state.rules.values() if any(r.get("title", "").startswith(f"{t} - ") for t in feeds)}
    for item in _candidates(plan, ownership.ROUTING_RULE, recorded, state.rules, rule_titles):
        targets = set(_ROUTE_TO.findall(state.rules[item.graylog_id].get("source") or ""))
        users = [p for p in state.pipelines if item.title in state.pipeline_rules(p) and p not in removable_pipelines]
        if not targets or not targets <= feeds:
            plan.items.append(_conflict(item, "does not route to the customer's UBA feed streams"))
        elif users:
            titles = ", ".join(state.pipelines[p].get("title", p) for p in users)
            plan.items.append(_conflict(item, f"also run by pipeline(s) {titles}"))
        else:
            item.source = item.source or next((s for t, s in feed_titles.items() if item.title.startswith(f"{t} - ")), None)
            plan.items.append(item)
    removable_rules = {i.title for i in plan.of(ownership.ROUTING_RULE)}

    # A feed stream another rule still routes to stays (that rule would route to nothing).
    for item in plan.of(ownership.FEED_STREAM):
        routing_here = [
            r["title"]
            for r in state.rules.values()
            if item.title in _ROUTE_TO.findall(r.get("source") or "") and r["title"] not in removable_rules
        ]
        others = [p for p in state.connections.get(item.graylog_id, [])]
        definitions = state.definitions_on(item.graylog_id)
        if routing_here:
            _conflict(item, f"rule(s) UBA setup did not make route to it: {', '.join(routing_here[:5])}")
        elif others:
            _conflict(item, f"{len(others)} pipeline(s) are connected to it")
        elif definitions:
            _conflict(item, f"event definition(s) read it: {', '.join(d.get('title', d.get('id')) for d in definitions[:5])}")

    # The output to UBA: detached from the feed streams; deleted when attached to nothing else.
    output_title = names["output"].format(tenant=code)
    feed_ids = {i.graylog_id for i in plan.of(ownership.FEED_STREAM, None)}
    for item in _candidates(plan, ownership.OUTPUT, recorded, state.outputs, {output_title: None}):
        output = state.outputs[item.graylog_id]
        elsewhere = [s for s in state.output_streams(item.graylog_id) if s not in feed_ids]
        if output.get("type") not in (None, GELF_OUTPUT) or not item.title.startswith("UBA GELF - "):
            plan.items.append(_conflict(item, "is not a UBA GELF output"))
        elif elsewhere:
            item.action = "keep"
            titles = ", ".join(state.streams[s].get("title", s) for s in elsewhere[:5])
            item.detail = f"also attached to {titles}: only detached from the customer's feed streams"
            plan.items.append(item)
        else:
            cfg = output.get("configuration") or {}
            item.detail = f"-> {cfg.get('hostname')}:{cfg.get('port')}"
            plan.items.append(item)

    # The customer's UBA ALERTS stream.
    alerts_title = names["alerts_stream"].format(tenant=code)
    for item in _candidates(plan, ownership.ALERTS_STREAM, recorded, state.streams, {alerts_title: None}):
        stream = state.streams[item.graylog_id]
        customer_rule = any(
            r.get("field") == "agent_labels_customer" and str(r.get("value", "")).lower() == code.lower() for r in stream.get("rules") or []
        )
        uses = [state.pipelines.get(p, {}).get("title", p) for p in state.connections.get(item.graylog_id, [])]
        uses += [f"event definition {d.get('title', d.get('id'))}" for d in state.definitions_on(item.graylog_id)]
        uses += [f"output {state.outputs.get(o, {}).get('title', o)}" for o in state.stream_outputs(item.graylog_id)]
        if item.graylog_id in protected or not item.title.startswith("UBA ALERTS - ") or not customer_rule:
            plan.items.append(_conflict(item, "does not look like the customer's UBA alerts stream"))
        elif uses:
            plan.items.append(_conflict(item, f"still used by {', '.join(uses[:5])}"))
        else:
            item.detail = "its alerts stay in the index"
            plan.items.append(item)

    # The shared input: only once no customer has a UBA alerts stream left.
    removed_alerts = {i.graylog_id for i in plan.of(ownership.ALERTS_STREAM)}
    remaining = [
        s["title"] for s_id, s in state.streams.items() if s.get("title", "").startswith("UBA ALERTS - ") and s_id not in removed_alerts
    ]
    others = sorted(
        {
            r.customer_code
            for r in await ownership.active(session)
            if r.kind == ownership.ALERTS_STREAM and r.customer_code != code and r.graylog_id in state.streams
        },
    )
    input_title = names["alerts_input"]
    # Found by title only for a customer that has an alerts stream: the input is not anyone's in particular.
    input_titles = {input_title: None} if plan.of(ownership.ALERTS_STREAM, None) else {}
    for item in _candidates(plan, ownership.ALERTS_INPUT, recorded, state.inputs, input_titles):
        item.shared = True
        if state.inputs[item.graylog_id].get("type") not in (None, GELF_TCP_INPUT):
            plan.items.append(_conflict(item, "is not a GELF TCP input"))
        elif remaining or others:
            item.action = "keep"
            users = remaining[:5] or others[:5]
            item.detail = f"shared: still used by {', '.join(users)}"
            plan.items.append(item)
        else:
            item.detail = "shared, and no other customer has a UBA alerts stream"
            plan.items.append(item)

    # The Wazuh rules: never removed.
    for row in recorded.get(ownership.WAZUH_RULES, []):
        plan.items.append(
            Item(
                ownership.WAZUH_RULES,
                row.graylog_id,
                row.title,
                recorded=True,
                shared=True,
                action="keep",
                detail="shared by every customer on the Wazuh manager; removing them needs a manager restart",
            ),
        )
    return plan


def plan_response(plan: Plan) -> UbaRollbackPlan:
    remove = [i.out() for i in _ordered(plan.items) if i.action == "remove"]
    if plan.uba and plan.uba.get("active"):
        remove.append(
            UbaRollbackItem(
                kind="uba_tenant",
                id=plan.customer_code,
                title=f"UBA tenant {plan.customer_code}",
                detail="deactivated; its data is kept",
            ),
        )
    elif plan.uba is None and plan.uba_problem:
        remove.append(
            UbaRollbackItem(
                kind="uba_tenant",
                id=plan.customer_code,
                title=f"UBA tenant {plan.customer_code}",
                detail="UBA could not be asked: deactivating it is tried, and the rest of the rollback runs either way",
            ),
        )
    state = plan.state
    sources = [
        {
            "id": s,
            "title": (state.streams.get(s) or {}).get("title"),
            "exists": s in state.streams,
            "pipelines": [state.pipelines.get(p, {}).get("title", p) for p in state.connections.get(s, [])],
        }
        for s in plan.source_streams
    ]
    if remove:
        message = f"{len(remove)} object(s) to remove for {plan.customer_code}"
    else:
        message = f"UBA is not set up for {plan.customer_code}: nothing to roll back"
    return UbaRollbackPlan(
        message=message,
        remove=remove,
        keep=[i.out() for i in plan.items if i.action == "keep"],
        conflicts=[i.out() for i in plan.items if i.action == "conflict"],
        source_streams=sources,
        uba=plan.uba,
        uba_problem=plan.uba_problem,
    )


ORDER = [
    ownership.ROUTING_PIPELINE,
    ownership.OUTPUT,
    ownership.ROUTING_RULE,
    ownership.FEED_STREAM,
    ownership.ALERTS_STREAM,
    ownership.ALERTS_INPUT,
    ownership.WAZUH_RULES,
]


def _ordered(items: List[Item]) -> List[Item]:
    return sorted(items, key=lambda i: (ORDER.index(i.kind) if i.kind in ORDER else 99, i.source or "", i.title))


async def get_rollback_plan(customer_code: str, session: AsyncSession) -> UbaRollbackPlan:
    return plan_response(await build_plan(customer_code, session))


# -- doing it --------------------------------------------------------------------------------------


class _Run:
    def __init__(self) -> None:
        self.steps: List[UbaProvisionStep] = []
        self.removed: List[Item] = []
        self.disconnected: Set[str] = set()  # routing pipelines no longer connected to any stream
        self.failed = False

    def add(self, step: str, status: str, detail: str = "") -> None:
        logger.info(f"UBA rollback: {step}: {status} {detail}".rstrip())
        self.steps.append(UbaProvisionStep(step=step, status=status, detail=detail))
        if status == "failed":
            self.failed = True


async def _exists(endpoint: str) -> bool:
    try:
        await send_get_request(endpoint=endpoint)
        return True
    except HTTPException as e:
        if e.status_code == 404:
            return False
        raise


async def _delete(endpoint: str, check: Optional[str] = None) -> str:
    """Delete; "removed", or "gone" when it already was. Raises when Graylog refused."""
    try:
        result = await send_delete_request(endpoint=endpoint)
        if result.get("success"):
            return "removed"
        reason = result.get("message") or f"DELETE {endpoint} failed"
    except HTTPException as e:
        reason = str(e.detail)
    if not await _exists(check or endpoint):
        return "gone"
    raise HTTPException(status_code=502, detail=reason)


def _error(e: Exception) -> str:
    return str(e.detail) if isinstance(e, HTTPException) else (e.detail if isinstance(e, UbaRequestError) else str(e))


async def execute(plan: Plan, run: _Run) -> None:
    state = plan.state
    for item in plan.gone:
        run.removed.append(item)
        run.add(f"{item.kind} {item.title}", "gone", "no longer in Graylog")

    # 1. Stop the routing first: nothing new reaches the feed streams or the output after this.
    disconnected = run.disconnected
    for item in _ordered(plan.of(ownership.ROUTING_PIPELINE)):
        streams = state.pipeline_streams(item.graylog_id)
        try:
            if streams:
                await send_post_request(
                    endpoint="/api/system/pipelines/connections/to_pipeline",
                    data={"pipeline_id": item.graylog_id, "stream_ids": []},
                )
                run.add(f"pipeline {item.title}", "disconnected", f"from {len(streams)} stream(s)")
            disconnected.add(item.graylog_id)
        except Exception as e:
            run.add(f"pipeline {item.title}", "failed", f"could not be disconnected: {_error(e)}")
    stopped_sources = {i.source for i in plan.of(ownership.ROUTING_PIPELINE) if i.graylog_id not in disconnected}
    # A pipeline that is still connected keeps routing to its feed stream: that stream must stay,
    # and the rules it runs with it.

    # 2. The output.
    feed_ids = {i.graylog_id for i in plan.of(ownership.FEED_STREAM, None)}
    for item in plan.of(ownership.OUTPUT, None):
        if item.action == "conflict":
            continue
        try:
            for stream_id in state.output_streams(item.graylog_id):
                if stream_id in feed_ids:
                    await _delete(f"/api/streams/{stream_id}/outputs/{item.graylog_id}", f"/api/streams/{stream_id}")
                    run.add(f"output {item.title}", "detached", f"from {state.streams[stream_id].get('title', stream_id)}")
            if item.action == "remove":
                run.add(f"output {item.title}", await _delete(f"/api/system/outputs/{item.graylog_id}"))
                run.removed.append(item)
            else:
                run.add(f"output {item.title}", "kept", item.detail)
        except Exception as e:
            run.add(f"output {item.title}", "failed", _error(e))

    # 3. Pipelines, then their rules.
    for item in _ordered(plan.of(ownership.ROUTING_PIPELINE)):
        if item.graylog_id not in disconnected:
            continue
        try:
            run.add(f"pipeline {item.title}", await _delete(f"/api/system/pipelines/pipeline/{item.graylog_id}"))
            run.removed.append(item)
        except Exception as e:
            stopped_sources.add(item.source)
            run.add(f"pipeline {item.title}", "failed", _error(e))
    deleted_pipelines = {i.graylog_id for i in run.removed if i.kind == ownership.ROUTING_PIPELINE}
    for item in _ordered(plan.of(ownership.ROUTING_RULE)):
        runners = [p for p in state.pipelines if item.title in state.pipeline_rules(p) and p not in deleted_pipelines]
        if runners:
            run.add(f"rule {item.title}", "skipped", "its pipeline could not be removed")
            continue
        try:
            run.add(f"rule {item.title}", await _delete(f"/api/system/pipelines/rule/{item.graylog_id}"))
            run.removed.append(item)
        except Exception as e:
            run.add(f"rule {item.title}", "failed", _error(e))

    # 4. Feed streams, unless their routing is still in place.
    for item in _ordered(plan.of(ownership.FEED_STREAM)):
        if item.source in stopped_sources:
            run.add(f"stream {item.title}", "skipped", "its routing pipeline is still in place")
            continue
        try:
            run.add(f"stream {item.title}", await _delete(f"/api/streams/{item.graylog_id}"))
            run.removed.append(item)
        except Exception as e:
            run.add(f"stream {item.title}", "failed", _error(e))

    # 5. Alerts stream, then the shared input.
    for item in plan.of(ownership.ALERTS_STREAM):
        try:
            run.add(f"stream {item.title}", await _delete(f"/api/streams/{item.graylog_id}"), item.detail)
            run.removed.append(item)
        except Exception as e:
            run.add(f"stream {item.title}", "failed", _error(e))
    alerts_left = any(i.kind == ownership.ALERTS_STREAM and i.action == "remove" and i not in run.removed for i in plan.items)
    for item in plan.of(ownership.ALERTS_INPUT, None):
        if item.action != "remove" or alerts_left:
            run.add(
                f"input {item.title}",
                "kept",
                item.detail if item.action != "remove" else "the customer's alerts stream is still there",
            )
            continue
        try:
            run.add(f"input {item.title}", await _delete(f"/api/system/inputs/{item.graylog_id}"), item.detail)
            run.removed.append(item)
        except Exception as e:
            run.add(f"input {item.title}", "failed", _error(e))

    for item in plan.items:
        if item.action == "conflict":
            run.add(f"{item.kind} {item.title}", "conflict", f"left alone: {item.detail}")
        elif item.kind == ownership.WAZUH_RULES:
            run.add(f"Wazuh rules {item.title}", "kept", item.detail)

    # 6. UBA, last: the Graylog side no longer sends it anything.
    if plan.uba is None and plan.uba_problem is None:
        run.add("UBA tenant", "skipped", "UBA does not know this customer")
    elif plan.uba is not None and not plan.uba.get("active"):
        run.add("UBA tenant", "skipped", "already inactive")
    else:
        try:
            await uba_request("PUT", f"/v1/tenants/{path_segment(plan.customer_code)}", json={"active": False})
            run.add("UBA tenant", "deactivated", "its entities, alerts and verdicts are kept")
        except UbaRequestError as e:
            if e.status_code == 404:
                run.add("UBA tenant", "skipped", "UBA does not know this customer")
            else:
                run.add("UBA tenant", "failed", f"{e.detail}: Graylog no longer sends UBA anything; roll back again once UBA answers")


# -- checking it -----------------------------------------------------------------------------------


def _definition_fingerprint(definitions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {d.get("id"): d.get("state") for d in definitions}


async def verify(plan: Plan, run: _Run) -> List[UbaRollbackCheck]:
    before = plan.state
    checks: List[UbaRollbackCheck] = []
    try:
        after = await read_graylog()
    except Exception as e:
        return [UbaRollbackCheck(check="Graylog read back", ok=None, detail=_error(e))]
    removed_pipelines = run.disconnected | {i.graylog_id for i in run.removed if i.kind == ownership.ROUTING_PIPELINE}
    for stream_id in plan.source_streams:
        title = (before.streams.get(stream_id) or {}).get("title") or stream_id
        was, now = before.streams.get(stream_id), after.streams.get(stream_id)
        if was is None:
            checks.append(UbaRollbackCheck(check=f"stream {title}", ok=None, detail="not in Graylog before the rollback either"))
            continue
        running = now is not None and bool(now.get("disabled")) == bool(was.get("disabled"))
        state_text = "paused" if now and now.get("disabled") else "running"
        checks.append(UbaRollbackCheck(check=f"stream {title}", ok=running, detail=state_text if now else "gone"))
        expected = sorted(p for p in before.connections.get(stream_id, []) if p not in removed_pipelines)
        kept = sorted(after.connections.get(stream_id, []))
        names = ", ".join(after.pipelines.get(p, {}).get("title", p) for p in kept) or "none"
        checks.append(
            UbaRollbackCheck(
                check=f"pipelines of {title}",
                ok=kept == expected,
                detail=f"{len(kept)} kept: {names}" if kept == expected else f"expected {len(expected)}, found {len(kept)}: {names}",
            ),
        )
    if before.event_definitions is None or after.event_definitions is None:
        checks.append(UbaRollbackCheck(check="event definitions", ok=None, detail="Graylog's event definitions could not be read"))
    else:
        same = _definition_fingerprint(before.event_definitions) == _definition_fingerprint(after.event_definitions)
        checks.append(
            UbaRollbackCheck(
                check="event definitions",
                ok=same,
                detail=f"{len(after.event_definitions)} unchanged"
                if same
                else f"{len(before.event_definitions)} before, {len(after.event_definitions)} after",
            ),
        )
    left = [p for p in removed_pipelines if any(p in ids for ids in after.connections.values())]
    checks.append(
        UbaRollbackCheck(check="UBA routing", ok=not left, detail="no routing to UBA left" if not left else f"{len(left)} still connected"),
    )
    removed_outputs = {i.graylog_id for i in run.removed if i.kind == ownership.OUTPUT}
    feeds = {i.graylog_id for i in plan.of(ownership.FEED_STREAM, None)}
    attached = [o for o in removed_outputs if o in after.outputs] + [
        i.graylog_id for i in plan.of(ownership.OUTPUT, None) if i.action != "conflict" and set(after.output_streams(i.graylog_id)) & feeds
    ]
    checks.append(
        UbaRollbackCheck(
            check="output to UBA",
            ok=not attached,
            detail="no stream of the customer sends to UBA" if not attached else "still attached",
        ),
    )
    if any(s.step == "UBA tenant" and s.status == "deactivated" for s in run.steps):
        onboarding, problem = await _onboarding(plan.customer_code)
        inactive = onboarding is None or not onboarding.get("active")
        checks.append(
            UbaRollbackCheck(
                check="UBA tenant",
                ok=None if problem else inactive,
                detail=problem or ("inactive" if inactive else "still active"),
            ),
        )
    return checks


# -- entry points ----------------------------------------------------------------------------------


def _snapshot(plan: Plan) -> Dict[str, Any]:
    state = plan.state
    store = {
        ownership.FEED_STREAM: state.streams,
        ownership.ALERTS_STREAM: state.streams,
        ownership.ROUTING_PIPELINE: state.pipelines,
        ownership.ROUTING_RULE: state.rules,
        ownership.OUTPUT: state.outputs,
        ownership.ALERTS_INPUT: state.inputs,
    }
    objects = [{"kind": i.kind, "action": i.action, "object": store[i.kind].get(i.graylog_id)} for i in plan.items if i.kind in store]
    return {
        "taken_at": now_utc().isoformat(),
        "names": plan.names,
        "uba": plan.uba,
        "objects": objects,
        "connections": {
            pid: state.pipeline_streams(pid) for pid in (i.graylog_id for i in plan.items if i.kind == ownership.ROUTING_PIPELINE)
        },
        "source_streams": [
            {
                "id": s,
                "title": (state.streams.get(s) or {}).get("title"),
                "disabled": (state.streams.get(s) or {}).get("disabled"),
                "pipelines": state.connections.get(s, []),
            }
            for s in plan.source_streams
        ],
        "event_definitions": None
        if state.event_definitions is None
        else [{"id": d.get("id"), "title": d.get("title"), "state": d.get("state")} for d in state.event_definitions],
    }


async def roll_back(
    customer_code: str,
    session: AsyncSession,
    actor_user_id: Optional[int],
    actor_username: Optional[str],
) -> UbaRollbackReport:
    running = await session.execute(
        select(UbaRollback).where(
            UbaRollback.customer_code == customer_code,
            UbaRollback.status == "running",
            UbaRollback.started_at > to_naive_utc(now_utc() - RUNNING_FOR),
        ),
    )
    if running.scalars().first() is not None:
        raise HTTPException(status_code=409, detail=f"A UBA rollback of {customer_code} is already running")

    plan = await build_plan(customer_code, session)
    preview = plan_response(plan)
    if not preview.remove and not plan.gone:
        raise HTTPException(status_code=409, detail=preview.message)

    record = UbaRollback(
        customer_code=customer_code,
        status="running",
        started_at=now_utc(),
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        snapshot=_snapshot(plan),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    run = _Run()
    try:
        await execute(plan, run)
        checks = await verify(plan, run)
    except Exception as e:  # never leave the row "running"
        logger.exception(f"UBA rollback of {customer_code} stopped")
        run.add("rollback", "failed", _error(e))
        checks = []
    unverified = any(c.ok is False for c in checks)
    record.status = "partial" if run.failed or unverified else "completed"
    conflicts = sum(1 for s in run.steps if s.status == "conflict")
    removed = sum(1 for s in run.steps if s.status in ("removed", "gone"))
    record.message = (
        f"UBA rolled back for {customer_code}: {removed} object(s) removed"
        + (f", {conflicts} left for review" if conflicts else "")
        + ("" if record.status == "completed" else "; some steps failed or a check did not pass: run the rollback again")
    )
    record.steps = [s.model_dump() for s in run.steps]
    record.verification = [c.model_dump() for c in checks]
    record.finished_at = now_utc()
    await ownership.mark_removed(session, customer_code, [i.owned() for i in run.removed], record.id)
    await session.commit()
    await session.refresh(record)
    return UbaRollbackReport.model_validate(record)


async def list_rollbacks(customer_code: str, session: AsyncSession, limit: int = 20) -> List[UbaRollback]:
    rows = await session.execute(
        select(UbaRollback).where(UbaRollback.customer_code == customer_code).order_by(UbaRollback.id.desc()).limit(limit),
    )
    return list(rows.scalars().all())


async def get_rollback(customer_code: str, rollback_id: int, session: AsyncSession) -> UbaRollbackReport:
    row = await session.get(UbaRollback, rollback_id)
    if row is None or row.customer_code != customer_code:  # 404, not 403: ids cannot be probed across tenants
        raise HTTPException(status_code=404, detail="UBA rollback not found")
    return UbaRollbackReport.model_validate(row)
