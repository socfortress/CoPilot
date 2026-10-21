"""A stand-in for the Wazuh indexer and manager, for the Exposure page's tests (#1289). Not
collected by pytest.

``FakeIndexer`` evaluates exactly the query DSL ``exposure_vulnerabilities`` builds — bool
filters of term / terms / prefix / wildcard and the agent pair script, and terms, cardinality, max, min, filter and
bucket_sort aggregations — over documents shaped like Wazuh's vulnerability states, and
records every body it is asked, so a test can check both what the page shows and what Wazuh
was told (never another customer's agents). ``FakeManager`` answers ``GET /sca/{agent}``.
"""

from __future__ import annotations

import fnmatch
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional

from fastapi import HTTPException

from app.agents.wazuh.schema.agents import WazuhAgentScaResponse
from app.agents.wazuh.schema.agents import WazuhAgentScaResults


def vuln(
    agent_id: str,
    agent_name: str,
    cve: str,
    severity: str = "High",
    score: Optional[float] = 7.5,
    package: str = "openssl",
    version: str = "1.0",
    detected: str = "2026-09-01T10:00:00Z",
    published: str = "2026-08-01T00:00:00Z",
    description: str = "A flaw",
    reference: str = "https://example.org/a, https://example.org/b",
) -> dict:
    """One vulnerability-state document, as Wazuh stores it."""
    return {
        "agent": {"id": agent_id, "name": agent_name},
        "package": {"name": package, "version": version},
        "vulnerability": {
            "id": cve,
            "severity": severity,
            "score": {"base": score},
            "detected_at": detected,
            "published_at": published,
            "description": description,
            "reference": reference,
        },
    }


def _get(doc: dict, dotted: str) -> Any:
    value: Any = doc
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _matches(doc: dict, clause: dict) -> bool:
    ((kind, spec),) = clause.items()
    if kind == "match_all":
        return True
    if kind == "bool":
        return all(_matches(doc, inner) for inner in spec.get("filter", []))
    if kind == "script":
        script = spec["script"]
        assert "params.pairs.containsKey" in script["source"], "FakeIndexer knows only the agent pair script"
        key = f"{_get(doc, 'agent.id') or ''}|{_get(doc, 'agent.name') or ''}"
        return key in script["params"]["pairs"]
    ((field, value),) = spec.items()
    actual = _get(doc, field)
    if kind == "terms":
        return actual in value
    if kind == "term":
        return actual == value
    if kind == "prefix":
        return isinstance(actual, str) and actual.startswith(value)
    if kind == "wildcard":
        pattern = value["value"]
        if value.get("case_insensitive"):
            return isinstance(actual, str) and fnmatch.fnmatchcase(actual.lower(), pattern.lower())
        return isinstance(actual, str) and fnmatch.fnmatchcase(actual, pattern)
    raise AssertionError(f"FakeIndexer does not know the {kind} query")


def _millis(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def _metric(kind: str, spec: dict, docs: List[dict]) -> dict:
    values = [_get(doc, spec["field"]) for doc in docs]
    values = [value for value in values if value is not None]
    if kind == "cardinality":
        return {"value": len(set(values))}
    if not values:
        return {"value": None}
    if isinstance(values[0], str):
        chosen = (min if kind == "min" else max)(values, key=_millis)
        millis = _millis(chosen)
        return {
            "value": millis,
            "value_as_string": datetime.fromtimestamp(millis / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
    return {"value": float((min if kind == "min" else max)(values))}


def _sort_value(bucket: dict, name: str, gap_zero: bool):
    if name == "_key":
        return bucket["key"]
    if name == "_count":
        return bucket["doc_count"]
    value = bucket[name]["value"]
    return 0 if value is None and gap_zero else value


def _aggregate(aggs: dict, docs: List[dict]) -> dict:
    out = {}
    for name, spec in aggs.items():
        spec = dict(spec)
        sub = spec.pop("aggs", {})
        ((kind, body),) = spec.items()
        if kind in ("cardinality", "max", "min"):
            out[name] = _metric(kind, body, docs)
        elif kind == "filter":
            inner = [doc for doc in docs if _matches(doc, body)]
            out[name] = {"doc_count": len(inner), **_aggregate(sub, inner)}
        elif kind == "terms":
            groups: Dict[Any, List[dict]] = {}
            for doc in docs:
                key = _get(doc, body["field"])
                if key is not None:
                    groups.setdefault(key, []).append(doc)
            pipelines = {key: value for key, value in sub.items() if "bucket_sort" in value}
            metrics = {key: value for key, value in sub.items() if key not in pipelines}
            buckets = [{"key": key, "doc_count": len(group), **_aggregate(metrics, group)} for key, group in groups.items()]
            order = body.get("order")
            if order:
                ((metric, direction),) = order.items()
                buckets.sort(key=lambda b: (_sort_value(b, metric, True), b["key"]), reverse=direction == "desc")
            else:
                buckets.sort(key=lambda b: (-b["doc_count"], b["key"]))
            buckets = buckets[: body.get("size", 10)]
            for pipeline in pipelines.values():
                rule = pipeline["bucket_sort"]
                gap_zero = rule.get("gap_policy") == "insert_zeros"
                for item in reversed(rule.get("sort", [])):
                    ((metric, how),) = item.items()
                    buckets.sort(key=lambda b: _sort_value(b, metric, gap_zero), reverse=how["order"] == "desc")
                start = rule.get("from", 0)
                buckets = buckets[start : start + rule.get("size", len(buckets))]
            out[name] = {"buckets": buckets}
        else:
            raise AssertionError(f"FakeIndexer does not know the {kind} aggregation")
    return out


def _sorted_hits(docs: List[dict], sort: Iterable) -> List[dict]:
    result = list(docs)
    for item in reversed(list(sort or [])):
        if item == "_doc":
            continue
        ((field, how),) = item.items()
        present = [doc for doc in result if _get(doc, field) is not None]
        missing = [doc for doc in result if _get(doc, field) is None]
        present.sort(key=lambda doc: _get(doc, field), reverse=how.get("order") == "desc")
        result = present + missing
    return result


class FakeIndexer:
    """The vulnerability states of a deployment, answering the Exposure page's queries."""

    def __init__(self, docs: List[dict], fail: bool = False):
        self.docs = docs
        self.fail = fail
        self.bodies: List[dict] = []

    def _select(self, body: dict) -> List[dict]:
        return [doc for doc in self.docs if _matches(doc, body.get("query", {"match_all": {}}))]

    async def search(self, body: dict) -> dict:
        self.bodies.append(body)
        if self.fail:
            raise ConnectionError("indexer at 10.0.0.9:9200 refused the connection")
        docs = self._select(body)
        hits = _sorted_hits(docs, body.get("sort"))[: body.get("size", 10)]
        return {
            "hits": {"total": {"value": len(docs)}, "hits": [{"_source": doc} for doc in hits]},
            "aggregations": _aggregate(body.get("aggs", {}), docs),
        }

    async def scroll(self, body: dict):
        self.bodies.append(body)
        if self.fail:
            raise ConnectionError("indexer at 10.0.0.9:9200 refused the connection")
        docs = self._select(body)
        size = body.get("size", 10)
        for start in range(0, len(docs), size):
            yield [{"_source": doc} for doc in docs[start : start + size]]

    def asked_agents(self) -> set:
        """Every agent id any query was filtered to."""
        asked = set()
        for body in self.bodies:
            for clause in body.get("query", {}).get("bool", {}).get("filter", []):
                asked.update(clause.get("terms", {}).get("agent.id", []))
        return asked


def sca(
    policy_id: str,
    score: int,
    name: Optional[str] = None,
    passed: int = 10,
    failed: int = 5,
    invalid: int = 0,
) -> WazuhAgentScaResults:
    return WazuhAgentScaResults(
        policy_id=policy_id,
        name=name or f"Policy {policy_id}",
        description=f"About {policy_id}",
        score=score,
        total_checks=passed + failed + invalid,
        invalid=invalid,
        end_scan="2026-10-01T08:00:00Z",
        **{"pass": passed, "fail": failed},
    )


class FakeManager:
    """``GET /sca/{agent}`` of a Wazuh manager: policies per agent id, or a failure."""

    def __init__(self, policies: Dict[str, List[WazuhAgentScaResults]], failing: Iterable[str] = ()):
        self.policies = policies
        self.failing = set(failing)
        self.asked: List[str] = []

    async def collect_agent_sca(self, agent_id: str, policy_id: str = None) -> WazuhAgentScaResponse:
        self.asked.append(agent_id)
        if agent_id in self.failing:
            raise HTTPException(status_code=500, detail="Wazuh API at 10.0.0.8:55000: connection reset")
        return WazuhAgentScaResponse(sca=self.policies.get(agent_id, []), success=True, message="ok")


__all__ = ["FakeIndexer", "FakeManager", "sca", "vuln"]
