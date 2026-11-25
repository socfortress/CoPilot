r"""Test doubles for the Sysmon noise statistics: an indexer that evaluates the collector's aggregations over synthetic
Sysmon alerts, MinIO in memory, the SQLite tables, and alert builders.

Every value here is synthetic (Contoso, Fabrikam, WS-0142): never a real customer, host or config. Alerts are stored as
Wazuh stores them: eventdata values JSON-escaped once more than Sysmon logged them (C:\\Windows for C:\Windows).
"""
import asyncio
import fnmatch
import json
from datetime import datetime
from datetime import timezone
from types import SimpleNamespace
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from miniopy_async.error import S3Error
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

CHANNEL = "Microsoft-Windows-Sysmon/Operational"
BUCKET = "sysmon-config-defaults"
DAY_MS = 86_400_000

# ---- alerts ---------------------------------------------------------------------------------------------------------

BASE_FIELDS = {
    "flat": {
        "label": "agent_labels_customer",
        "agent": "agent_id",
        "level": "rule_level",
        "event_id": "data_win_system_eventID",
        "channel": "data_win_system_channel",
        "computer": "data_win_system_computer",
        "prefix": "data_win_eventdata_",
    },
    "nested": {
        "label": "agent.labels.customer",
        "agent": "agent.id",
        "level": "rule.level",
        "event_id": "data.win.system.eventID",
        "channel": "data.win.system.channel",
        "computer": "data.win.system.computer",
        "prefix": "data.win.eventdata.",
    },
}


def wazuh_escaped(value: str) -> str:
    """How Wazuh's eventchannel decoder stores a value: JSON-escaped once more than Sysmon logged it."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def lower_camel(name: str) -> str:
    return name[0].lower() + name[1:]


def ms(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def alert(
    *,
    eid: int,
    ts: int,
    agent: str,
    label: Optional[str],
    level: int = 3,
    shape: str = "nested",
    channel: str = CHANNEL,
    escaped: bool = True,
    computer: Optional[str] = None,
    **eventdata: str,
) -> Dict[str, Any]:
    """One Sysmon alert as the indexer holds it, flattened to its field paths. ``computer`` is the Windows event's
    Computer (a domain-joined endpoint's fully qualified name)."""
    f = BASE_FIELDS[shape]
    doc: Dict[str, Any] = {
        "timestamp": ts,
        f["agent"]: agent,
        f["level"]: level,
        f["event_id"]: str(eid),
        f["channel"]: channel,
    }
    if label is not None:
        doc[f["label"]] = label
    if computer is not None:
        doc[f["computer"]] = computer
    for name, value in eventdata.items():
        doc[f["prefix"] + lower_camel(name)] = wazuh_escaped(value) if escaped else value
    return doc


# ---- the indexer ----------------------------------------------------------------------------------------------------


def _matches(doc: Dict[str, Any], clause: Dict[str, Any]) -> bool:
    if "bool" in clause:
        return all(_matches(doc, c) for c in clause["bool"].get("filter", []))
    if "range" in clause:
        ((name, spec),) = clause["range"].items()
        value = doc.get(name)
        if value is None:
            return False
        return (spec.get("gte") is None or value >= spec["gte"]) and (spec.get("lt") is None or value < spec["lt"])
    if "term" in clause:
        ((name, wanted),) = clause["term"].items()
        return name in doc and str(doc[name]) == str(wanted)
    if "terms" in clause:
        ((name, wanted),) = clause["terms"].items()
        return name in doc and str(doc[name]) in {str(w) for w in wanted}
    raise AssertionError(f"unsupported query clause {clause}")


def _aggregate(docs: List[Dict[str, Any]], aggs: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, spec in aggs.items():
        sub = spec.get("aggs") or {}
        if "terms" in spec:
            terms = spec["terms"]
            groups: Dict[Any, List[Dict[str, Any]]] = {}
            for doc in docs:
                if terms["field"] in doc:
                    key = doc[terms["field"]]
                elif "missing" in terms:
                    key = terms["missing"]
                else:
                    continue
                groups.setdefault(key, []).append(doc)
            ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))
            kept = ordered[: terms["size"]]
            out[name] = {
                "doc_count_error_upper_bound": 0,
                "sum_other_doc_count": sum(len(g) for _, g in ordered[terms["size"] :]),
                "buckets": [{"key": k, "doc_count": len(g), **_aggregate(g, sub)} for k, g in kept],
            }
        elif "cardinality" in spec:
            out[name] = {"value": len({doc[spec["cardinality"]["field"]] for doc in docs if spec["cardinality"]["field"] in doc})}
        elif "filter" in spec:
            kept = [doc for doc in docs if _matches(doc, spec["filter"])]
            out[name] = {"doc_count": len(kept), **_aggregate(kept, sub)}
        elif "date_histogram" in spec:
            field = spec["date_histogram"]["field"]
            days: Dict[int, List[Dict[str, Any]]] = {}
            for doc in docs:
                days.setdefault(doc[field] // DAY_MS * DAY_MS, []).append(doc)
            out[name] = {
                "buckets": [
                    {"key": k, "key_as_string": str(k), "doc_count": len(g), **_aggregate(g, sub)} for k, g in sorted(days.items())
                ],
            }
        else:
            raise AssertionError(f"unsupported aggregation {spec}")
    return out


def evaluate(body: Dict[str, Any], docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    assert body["size"] == 0 and body["track_total_hits"] is False
    query = body.get("query") or {"bool": {"filter": []}}
    matched = [doc for doc in docs if _matches(doc, query)]
    return {
        "took": 1,
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
        "hits": {"hits": []},
        "aggregations": _aggregate(matched, body.get("aggs") or {}),
    }


def field_caps(docs: List[Dict[str, Any]], patterns: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    wanted = [p.strip() for p in patterns.split(",") if p.strip()]
    names = set()
    for doc in docs:
        names.update(doc)
    caps: Dict[str, Any] = {}
    for name in sorted(names):
        if not any(fnmatch.fnmatchcase(name, p) for p in wanted):
            continue
        if name == "timestamp":
            caps[name] = {"date": {"type": "date", "searchable": True, "aggregatable": True}}
        elif name in ("rule.level", "rule_level"):
            caps[name] = {"long": {"type": "long", "searchable": True, "aggregatable": True}}
        else:
            caps[name] = {"keyword": {"type": "keyword", "searchable": True, "aggregatable": True}}
    caps.update(overrides or {})
    return {"indices": ["wazuh-alerts-4.x-2026.11.20"], "fields": caps}


class _Tasks:
    def __init__(self, indexer):
        self.indexer = indexer
        self.cancelled: List[str] = []

    async def list(self, **kwargs):
        return {
            "nodes": {
                "n1": {"tasks": {f"n1:{i}": {"headers": {"X-Opaque-Id": o}} for i, o in enumerate(self.indexer.opaque_ids)}},
            },
        }

    async def cancel(self, task_id, **kwargs):
        self.cancelled.append(task_id)


def stage_of(body: Dict[str, Any]) -> str:
    aggs = body.get("aggs") or {}
    if "labels" in aggs:
        return "labels"
    if "quiet" in aggs:
        return "quiet"
    if "actor" in aggs:
        eid = next(c["term"] for c in body["query"]["bool"]["filter"] if "term" in c and "Sysmon" not in json.dumps(c))
        return f"actor{list(eid.values())[0]}"
    return "unknown"


class FakeIndexer:
    """Answers field_caps and search over ``docs``; ``answers`` replaces a stage's answer (a response or an exception)."""

    def __init__(
        self,
        docs=None,
        *,
        answers=None,
        caps_overrides=None,
        field_caps_error=None,
        delay=0.0,
        history_caps=None,
        week_indices=None,
    ):
        self.docs = list(docs or [])
        self.answers = dict(answers or {})
        self.caps_overrides = caps_overrides
        # Mappings only an index outside the asked week has: what field_caps answers without an index_filter
        self.history_caps = history_caps
        # The indices field_caps names when asked with an index_filter (None: it names the one default index)
        self.week_indices = week_indices
        self.field_caps_error = field_caps_error
        self.delay = delay
        self.searches: List[Dict[str, Any]] = []
        self.field_caps_calls: List[Dict[str, Any]] = []
        self.opaque_ids: List[str] = []
        self.tasks = _Tasks(self)
        self.closed = False
        self.in_flight = 0
        self.max_in_flight = 0

    async def field_caps(self, **kwargs):
        self.field_caps_calls.append(kwargs)
        if self.field_caps_error is not None:
            raise self.field_caps_error
        filtered = "index_filter" in (kwargs.get("body") or {})
        overrides = dict(self.caps_overrides or {})
        if not filtered:
            overrides.update(self.history_caps or {})
        answer = field_caps(self.docs, kwargs["fields"], overrides)
        if filtered and self.week_indices is not None:
            answer["indices"] = list(self.week_indices)
        return answer

    async def search(self, index, body, **kwargs):
        stage = stage_of(body)
        self.searches.append({"index": index, "body": body, "stage": stage, **kwargs})
        self.opaque_ids.append(kwargs.get("opaque_id"))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            answer = self.answers.get(stage)
            if isinstance(answer, BaseException):
                raise answer
            if answer is not None:
                return answer
            return evaluate(body, self.docs)
        finally:
            self.in_flight -= 1

    async def close(self):
        self.closed = True


# ---- MinIO ----------------------------------------------------------------------------------------------------------


class _Object:
    def __init__(self, content):
        self.content = content

    async def read(self):
        return self.content

    def close(self):
        pass


class FakeMinio:
    def __init__(self):
        self.objects: Dict[Any, bytes] = {}
        self.puts: List[str] = []
        self.removed: List[str] = []
        self.fail_put: Dict[str, Exception] = {}
        self.fail_get: Optional[Exception] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def bucket_exists(self, bucket):
        return True

    async def get_object(self, bucket, name):
        if self.fail_get is not None:
            raise self.fail_get
        if (bucket, name) not in self.objects:
            raise S3Error("NoSuchKey", "stub", f"/{bucket}/{name}", None, None, None)
        return _Object(self.objects[(bucket, name)])

    async def put_object(self, bucket, name, data, length, content_type):
        if name in self.fail_put:
            raise self.fail_put[name]
        content = data.read()
        assert len(content) == length
        self.objects[(bucket, name)] = content
        self.puts.append(name)

    async def remove_object(self, bucket, name):
        self.objects.pop((bucket, name), None)
        self.removed.append(name)

    async def list_objects(self, bucket, prefix="", recursive=False):
        for b, name in sorted(self.objects):
            if b == bucket and name.startswith(prefix):
                yield SimpleNamespace(object_name=name)

    def get(self, name):
        return self.objects.get((BUCKET, name))

    def json(self, name):
        raw = self.get(name)
        return None if raw is None else json.loads(raw)

    def names(self, prefix=""):
        return sorted(n for (b, n) in self.objects if b == BUCKET and n.startswith(prefix))


# ---- the database ---------------------------------------------------------------------------------------------------

TABLES = ["customers", "agents", "license", "sysmon_stats_customer_settings", "sysmon_stats_identity"]


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(self.engine.sync_engine, "connect")
        def _foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        import app.db.universal_models  # noqa: F401 - registers the tables

        tables = [SQLModel.metadata.tables[name] for name in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    def session(self) -> AsyncSession:
        return self.factory()

    async def dispose(self) -> None:
        await self.engine.dispose()


async def seed(db: Db, customers: Dict[str, str], *, license_key: Optional[str] = None, hostnames: Optional[Dict[str, List[str]]] = None):
    from app.db.universal_models import Agents
    from app.db.universal_models import Customers
    from app.db.universal_models import License

    async with db.session() as s:
        for code, name in customers.items():
            s.add(Customers(customer_code=code, customer_name=name, created_at=datetime(2026, 1, 1)))
        if license_key:
            s.add(License(license_key=license_key, customer_name="n", customer_email="e@example.invalid", company_name="c"))
        await s.commit()
        for code, hosts in (hostnames or {}).items():
            for i, host in enumerate(hosts):
                s.add(
                    Agents(
                        agent_id=f"{code}-{i:03d}",
                        ip_address="192.0.2.1",
                        os="Windows",
                        hostname=host,
                        label=code,
                        wazuh_last_seen=datetime(2026, 11, 20),
                        wazuh_agent_version="v4.14.6",
                        customer_code=code,
                    ),
                )
        await s.commit()


# ---- a whole CoPilot: database, MinIO, indexer, SOCFortress ---------------------------------------------------------

LICENSE_KEY = "LICENSE-abcdef-0123456789-SECRET"
SERVICE_URL = "https://sync.test"
FABRIKAM_AGENT = "C:\\Program Files\\Fabrikam\\agent.exe"


def week_docs(label: str, *, endpoints: int = 5, monday: str = "2026-11-16", prefix: str = "") -> List[Dict[str, Any]]:
    """A customer's quiet week: a vendor DNS query, a vendor registry write and a per-service-account AppData file on
    every endpoint every day, plus a detection (level 10) and an internal name that must never be sent."""
    docs = []
    start = ms(f"{monday}T09:00:00")
    for i in range(endpoints):
        agent = f"{prefix}{label}-{i:03d}"
        for day in range(7):
            ts = start + day * DAY_MS + i
            docs.append(
                alert(
                    eid=22,
                    ts=ts,
                    agent=agent,
                    label=label,
                    Image=FABRIKAM_AGENT,
                    QueryName="telemetry.fabrikam-example.com",
                    QueryStatus="0",
                    User="NT AUTHORITY\\SYSTEM",
                    RuleName="-",
                ),
            )
            docs.append(
                alert(
                    eid=13,
                    ts=ts,
                    agent=agent,
                    label=label,
                    Image=FABRIKAM_AGENT,
                    TargetObject="HKLM\\SOFTWARE\\Fabrikam\\Agent\\State",
                    EventType="SetValue",
                    User="NT AUTHORITY\\SYSTEM",
                    RuleName="-",
                ),
            )
            docs.append(
                alert(eid=22, ts=ts, agent=agent, label=label, level=10, Image="C:\\Windows\\Temp\\x.exe", QueryName="c2.example-bad.net"),
            )
            docs.append(alert(eid=22, ts=ts, agent=agent, label=label, Image=FABRIKAM_AGENT, QueryName="fileserver.corp"))
    return docs


class Sysmonsync:
    """SOCFortress's sysmon-sync, answering by route; every request kept. ``reports`` answers in turn (the last repeats)."""

    def __init__(self, *, probe=None, reports=None, withdraws=None, on_report=None):
        import httpx

        self.httpx = httpx
        self.probe_answer = probe if probe is not None else httpx.Response(401, json={"detail": "missing license key"})
        self.report_answers = list(reports or [self.stored()])
        self.withdraw_answers = list(
            withdraws or [httpx.Response(200, json={"result": "withdrawn", "scope": "customer", "reports_deleted": 1})],
        )
        self.on_report = on_report
        self.requests: List[Any] = []

    def stored(self, accepted=None):
        return self.httpx.Response(
            200,
            json={
                "result": "stored",
                "replaced": False,
                "week": "2026-W47",
                "patterns": {"received": 0, "accepted": accepted or 0, "rejected": 0},
                "rejected_by_reason": {},
                "rejected_patterns": [],
            },
        )

    @staticmethod
    def _next(answers):
        return answers.pop(0) if len(answers) > 1 else answers[0]

    async def handle(self, request):
        self.requests.append(request)
        if request.url.path == "/v1/sysmon/report/withdraw":
            answer = self._next(self.withdraw_answers)
        elif "authorization" not in request.headers:
            answer = self.probe_answer
        else:
            if self.on_report is not None:
                await self.on_report(request)
            answer = self._next(self.report_answers)
            if callable(answer):
                answer = answer(request)
        if isinstance(answer, Exception):
            raise answer
        return answer

    @property
    def transport(self):
        return self.httpx.MockTransport(self.handle)

    def reports(self):
        return [r for r in self.requests if r.url.path == "/v1/sysmon/report" and "authorization" in r.headers]

    def withdraws(self):
        return [r for r in self.requests if r.url.path == "/v1/sysmon/report/withdraw"]

    def probes(self):
        return [r for r in self.requests if r.url.path == "/v1/sysmon/report" and "authorization" not in r.headers]


class World:
    """One CoPilot for a test: its SQLite tables, MinIO, indexer and the stored Sysmon configs, all fakes."""

    def __init__(self, monkeypatch, docs=None, *, stored_configs=None):
        from unittest.mock import AsyncMock

        import app.data_store.data_store_operations as data_store
        from app.active_response.services.sysmon_stats import runner
        from app.active_response.services.sysmon_stats import sharing
        from app.db import named_lock

        self.db = Db()
        self.minio = FakeMinio()
        self.indexer = FakeIndexer(docs or [])
        self.stored_configs = dict(stored_configs or {})
        self.indexer_clients = 0
        monkeypatch.setattr(data_store, "create_session", AsyncMock(return_value=self.minio))
        monkeypatch.setattr(data_store, "create_bucket_if_not_exists", AsyncMock())
        monkeypatch.setattr(named_lock, "new_session", self.db.session)
        monkeypatch.setattr(sharing, "new_session", self.db.session)

        async def indexer_client():
            self.indexer_clients += 1
            return self.indexer

        async def stored(code):
            if code not in self.stored_configs:
                raise RuntimeError("no stored config")
            return self.stored_configs[code]

        monkeypatch.setattr(runner, "make_indexer_client", indexer_client)
        monkeypatch.setattr(runner, "download_sysmon_config", stored)
        monkeypatch.setenv("SOCFORTRESS_SYSMON_SYNC_URL", SERVICE_URL)
        for name in ("SYSMON_STATS_SHARING", "SYSMON_DEFAULT_SYNC", "SYSMON_STATS_MIN_ENDPOINTS", "SYSMON_STATS_MAX_RULE_LEVEL"):
            monkeypatch.delenv(name, raising=False)

    async def setup(self, customers=None, *, license_key=LICENSE_KEY, hostnames=None):
        await self.db.create()
        await seed(
            self.db,
            customers if customers is not None else {"contoso": "Contoso Ltd"},
            license_key=license_key,
            hostnames=hostnames,
        )
        return self

    def state(self):
        return self.minio.json("stats-state.json") or {}

    def week(self, week="2026-W47"):
        return (self.state().get("weeks") or {}).get(week) or {}
