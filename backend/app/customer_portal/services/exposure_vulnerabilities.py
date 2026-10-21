"""The Exposure page's vulnerabilities (#1289): Wazuh's vulnerability states across a tenant.

Read live from the indexer's ``wazuh-states-vulnerabilities*`` indices, the documents the
agent's own Vulnerabilities tab reads (#1256), and aggregated **in the indexer**: a large
tenant has hundreds of thousands of CVE × package × agent rows, which must never be pulled
into CoPilot to be counted.

* **Scope first.** Every query is filtered by the scope's agents, by the exact pair of Wazuh
  id and name (``ExposureScope``, ``PAIR_SCRIPT``): never by customer, which Wazuh does not
  know, never by name alone, which two customers can share, and never by an id alone, which
  is unique per manager only.
* **One request for the page**: the counts per severity (not narrowed by the severity
  filter, so they can serve as one), the totals and the ranked CVEs under the filter, then
  one more for the details of the page's CVEs. CVEs are ranked by their highest CVSS, then
  by how many agents they affect, at most ``CVE_RANK_LIMIT`` of them.
* **EPSS is best-effort** (``collect_epss_scores``, batched): an unreachable EPSS leaves the
  column empty, it never fails the page.
* **The indexer's errors stay in the log**: the response says only that the data could not
  be read.

The builders and parsers are pure, so the queries Wazuh receives and what the portal shows
are tested without an indexer (``tests/exposure_support.py`` evaluates exactly this DSL).
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.customer_portal.schema.exposure import SEVERITIES
from app.customer_portal.schema.exposure import CveAgent
from app.customer_portal.schema.exposure import CveDetailResponse
from app.customer_portal.schema.exposure import CveRow
from app.customer_portal.schema.exposure import ExposureTotals
from app.customer_portal.schema.exposure import SeverityCount
from app.customer_portal.schema.exposure import VulnerabilitiesResponse
from app.customer_portal.services.exposure import ExposureScope
from app.threat_intel.services.epss import collect_epss_scores

INDEX_PATTERN = "wazuh-states-vulnerabilities*"
#: How many distinct CVEs are ranked (the terms aggregation's size): well under the
#: indexer's bucket limit, and more than any page needs; past it the response says so.
CVE_RANK_LIMIT = 10000
MAX_PAGE_SIZE = 100
#: Agents listed for one CVE.
CVE_AGENTS_LIMIT = 1000
#: Rows of the CSV export, read in batches of EXPORT_BATCH.
EXPORT_LIMIT = 100000
EXPORT_BATCH = 5000
#: Precision of the distinct counts: exact below it.
CARDINALITY_PRECISION = 40000
#: A search longer than this matches nothing useful: it is cut.
SEARCH_MAX_LENGTH = 100

READ_ERROR = "The vulnerability data could not be read from Wazuh"
CVE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
CVE_LIKE = re.compile(r"^(cve|ghsa)-", re.IGNORECASE)

DOC_FIELDS = [
    "agent.id",
    "agent.name",
    "package.name",
    "package.version",
    "vulnerability.id",
    "vulnerability.severity",
    "vulnerability.score.base",
    "vulnerability.detected_at",
    "vulnerability.published_at",
    "vulnerability.description",
    "vulnerability.reference",
]


# ── the queries (pure) ────────────────────────────────────────────────────────


def _escape_wildcard(text: str) -> str:
    return re.sub(r"([\\*?])", r"\\\1", text)


def search_clause(search: Optional[str]) -> Optional[dict]:
    """A CVE id prefix, or a package name containing the text (any case); None for no search."""
    text = (search or "").strip()[:SEARCH_MAX_LENGTH]
    if not text:
        return None
    if CVE_LIKE.match(text):
        return {"prefix": {"vulnerability.id": text.upper()}}
    return {"wildcard": {"package.name": {"value": f"*{_escape_wildcard(text)}*", "case_insensitive": True}}}


#: Keeps a document only when its (agent id, agent name) is one of the scope's agents.
#: The two ``terms`` filters before it narrow the candidates cheaply, but alone they let a
#: document pairing one of the scope's ids with another of its names through: an agent of
#: another customer, on another manager, that happens to share an id with one agent and a
#: name with another. One script clause, whatever the number of agents (a bool clause per
#: agent would hit the indexer's clause limit on a large tenant).
PAIR_SCRIPT = (
    "String id = doc['agent.id'].size() == 0 ? '' : doc['agent.id'].value;"
    " String name = doc['agent.name'].size() == 0 ? '' : doc['agent.name'].value;"
    " return params.pairs.containsKey(id + '|' + name);"
)


def pair_key(agent_id: str, hostname: str) -> str:
    return f"{agent_id}|{hostname}"


def scope_filter(scope: ExposureScope, search: Optional[str] = None) -> List[dict]:
    """The scope's agents (by id, name and the exact pair), the four severities, and the search."""
    filters: List[dict] = [
        {"terms": {"agent.id": scope.agent_ids}},
        {"terms": {"agent.name": scope.hostnames}},
        {
            "script": {
                "script": {
                    "source": PAIR_SCRIPT,
                    "lang": "painless",
                    "params": {"pairs": {pair_key(agent.agent_id, agent.hostname): 1 for agent in scope.agents}},
                },
            },
        },
        {"terms": {"vulnerability.severity": SEVERITIES}},
    ]
    clause = search_clause(search)
    if clause:
        filters.append(clause)
    return filters


def _distinct(field_name: str) -> dict:
    return {"cardinality": {"field": field_name, "precision_threshold": CARDINALITY_PRECISION}}


def overview_body(scope: ExposureScope, severity: Optional[str], search: Optional[str], page: int, page_size: int) -> dict:
    """Counts per severity (unfiltered by it), totals and one page of ranked CVEs under the filter."""
    filtered = {"term": {"vulnerability.severity": severity}} if severity else {"match_all": {}}
    return {
        "size": 0,
        "track_total_hits": True,
        "query": {"bool": {"filter": scope_filter(scope, search)}},
        "aggs": {
            "severities": {
                "terms": {"field": "vulnerability.severity", "size": 10},
                "aggs": {"cves": _distinct("vulnerability.id"), "hosts": _distinct("agent.id")},
            },
            "filtered": {
                "filter": filtered,
                "aggs": {
                    "cves": _distinct("vulnerability.id"),
                    "hosts": _distinct("agent.id"),
                    "by_cve": {
                        "terms": {"field": "vulnerability.id", "size": CVE_RANK_LIMIT, "order": {"max_score": "desc"}},
                        "aggs": {
                            "max_score": {"max": {"field": "vulnerability.score.base"}},
                            "hosts": _distinct("agent.id"),
                            "page": {
                                "bucket_sort": {
                                    "sort": [{"max_score": {"order": "desc"}}, {"hosts": {"order": "desc"}}, {"_key": {"order": "asc"}}],
                                    "from": (page - 1) * page_size,
                                    "size": page_size,
                                    "gap_policy": "insert_zeros",
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def details_body(scope: ExposureScope, cve_ids: List[str]) -> dict:
    """Severity, packages and dates of the given CVEs, on the scope's agents."""
    return {
        "size": 0,
        "query": {"bool": {"filter": [*scope_filter(scope), {"terms": {"vulnerability.id": cve_ids}}]}},
        "aggs": {
            "by_cve": {
                "terms": {"field": "vulnerability.id", "size": len(cve_ids)},
                "aggs": {
                    "severity": {"terms": {"field": "vulnerability.severity", "size": 1}},
                    "packages": {"terms": {"field": "package.name", "size": 5}},
                    "first_detected": {"min": {"field": "vulnerability.detected_at"}},
                    "published": {"min": {"field": "vulnerability.published_at"}},
                },
            },
        },
    }


def cve_body(scope: ExposureScope, cve_id: str) -> dict:
    """The scope's documents of one CVE, one per agent × package, by agent name."""
    return {
        "size": CVE_AGENTS_LIMIT + 1,
        "_source": DOC_FIELDS,
        "query": {"bool": {"filter": [*scope_filter(scope), {"term": {"vulnerability.id": cve_id}}]}},
        "sort": [{"agent.name": {"order": "asc"}}, {"package.name": {"order": "asc", "missing": "_last"}}],
    }


def export_body(scope: ExposureScope, severity: Optional[str], search: Optional[str]) -> dict:
    filters = scope_filter(scope, search)
    if severity:
        filters.append({"term": {"vulnerability.severity": severity}})
    return {"size": EXPORT_BATCH, "_source": DOC_FIELDS, "query": {"bool": {"filter": filters}}, "sort": ["_doc"]}


# ── reading the answers (pure) ────────────────────────────────────────────────


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _value(agg: Optional[dict]) -> int:
    return _int((agg or {}).get("value"))


def utc_iso(value: Any) -> Optional[str]:
    """An indexer date (ISO 8601, epoch millis, or a min/max aggregation) as `YYYY-MM-DDTHH:MM:SSZ`."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            moment = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        else:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_agg(agg: Optional[dict]) -> Optional[str]:
    agg = agg or {}
    return utc_iso(agg.get("value_as_string") or agg.get("value"))


def cvss(value: Any) -> Optional[float]:
    """A CVSS score to its one decimal: the indexer stores it as a 32-bit float (9.8 reads 9.800000190734863)."""
    try:
        return round(float(value), 1) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_severities(aggregations: dict) -> List[SeverityCount]:
    buckets = {bucket.get("key"): bucket for bucket in (aggregations.get("severities") or {}).get("buckets", [])}
    return [
        SeverityCount(
            severity=level,
            cves=_value(buckets.get(level, {}).get("cves")),
            hosts=_value(buckets.get(level, {}).get("hosts")),
            findings=_int(buckets.get(level, {}).get("doc_count")),
        )
        for level in SEVERITIES
    ]


def parse_page(aggregations: dict) -> Tuple[ExposureTotals, List[Tuple[str, Optional[float], int]], int]:
    """The filter's totals, the page's ``(cve, cvss, hosts)`` and the distinct CVEs matching."""
    filtered = aggregations.get("filtered") or {}
    totals = ExposureTotals(
        cves=_value(filtered.get("cves")),
        hosts=_value(filtered.get("hosts")),
        findings=_int(filtered.get("doc_count")),
    )
    ranked = []
    for bucket in (filtered.get("by_cve") or {}).get("buckets", []):
        ranked.append((str(bucket.get("key")), cvss((bucket.get("max_score") or {}).get("value")), _value(bucket.get("hosts"))))
    return totals, ranked, totals.cves


def parse_details(aggregations: dict) -> Dict[str, dict]:
    details = {}
    for bucket in (aggregations.get("by_cve") or {}).get("buckets", []):
        severity = [item.get("key") for item in (bucket.get("severity") or {}).get("buckets", [])]
        details[str(bucket.get("key"))] = {
            "severity": severity[0] if severity else None,
            "packages": [str(item.get("key")) for item in (bucket.get("packages") or {}).get("buckets", [])],
            "first_detected": _date_agg(bucket.get("first_detected")),
            "published": _date_agg(bucket.get("published")),
        }
    return details


def references(raw: Any, limit: int = 20) -> List[str]:
    """Wazuh's references, a comma-separated string (or a list), as a list of at most ``limit``."""
    items = raw if isinstance(raw, list) else str(raw or "").split(",")
    return [item.strip() for item in items if str(item).strip()][:limit]


def _get(source: dict, dotted: str) -> Any:
    value: Any = source
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def parse_cve(cve_id: str, hits: List[dict], scope: ExposureScope) -> CveDetailResponse:
    """One CVE: what Wazuh says of it, and the scope's agents it affects (others are dropped)."""
    owners = scope.by_agent()
    agents: List[CveAgent] = []
    first: Optional[dict] = None
    for hit in hits[:CVE_AGENTS_LIMIT]:
        source = hit.get("_source") or {}
        owner = owners.get((str(_get(source, "agent.id") or ""), str(_get(source, "agent.name") or "")))
        if owner is None:
            continue
        first = first or source
        agents.append(
            CveAgent(
                agent_id=owner.agent_id,
                hostname=owner.hostname,
                customer_code=owner.customer_code,
                package=_get(source, "package.name"),
                version=_get(source, "package.version"),
                detected=utc_iso(_get(source, "vulnerability.detected_at")),
            ),
        )
    first = first or {}
    return CveDetailResponse(
        cve_id=cve_id,
        severity=_get(first, "vulnerability.severity"),
        cvss=cvss(_get(first, "vulnerability.score.base")),
        description=_get(first, "vulnerability.description"),
        references=references(_get(first, "vulnerability.reference")),
        published=utc_iso(_get(first, "vulnerability.published_at")),
        agents=agents,
        truncated=len(hits) > CVE_AGENTS_LIMIT,
    )


CSV_HEADER = ["CVE", "Severity", "CVSS", "EPSS", "Package", "Version", "Host", "Customer", "Detected (UTC)", "Published (UTC)"]


def csv_cell(value: Any) -> str:
    """A cell that a spreadsheet will never run as a formula: hosts name their own packages."""
    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def csv_row(source: dict, owner, epss: Dict[str, str]) -> List[str]:
    cve = _get(source, "vulnerability.id")
    return [
        csv_cell(value)
        for value in (
            cve,
            _get(source, "vulnerability.severity"),
            _get(source, "vulnerability.score.base"),
            epss.get(cve or "", ""),
            _get(source, "package.name"),
            _get(source, "package.version"),
            owner.hostname,
            owner.customer_code,
            utc_iso(_get(source, "vulnerability.detected_at")),
            utc_iso(_get(source, "vulnerability.published_at")),
        )
    ]


# ── the indexer (patched in tests) ────────────────────────────────────────────


async def indexer_search(body: dict) -> dict:
    """One search across the vulnerability states; a missing index is no match, not an error."""
    client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        return await client.search(index=INDEX_PATTERN, body=body, ignore_unavailable=True, allow_no_indices=True)
    finally:
        await client.close()


async def indexer_scroll(body: dict) -> AsyncIterator[List[dict]]:
    """Every document matching ``body``, a batch of hits at a time."""
    client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    scroll_id = None
    try:
        page = await client.search(index=INDEX_PATTERN, body=body, scroll="2m", ignore_unavailable=True, allow_no_indices=True)
        while True:
            scroll_id = page.get("_scroll_id")
            hits = page.get("hits", {}).get("hits", [])
            if not hits:
                return
            yield hits
            page = await client.scroll(scroll_id=scroll_id, scroll="2m")
    finally:
        if scroll_id:
            try:
                await client.clear_scroll(scroll_id=scroll_id)
            except Exception as e:  # the context expires on its own
                logger.warning(f"Could not clear a vulnerability export scroll: {type(e).__name__}")
        await client.close()


async def epss_scores(cves: Iterable[str]) -> Dict[str, str]:
    return await collect_epss_scores(cves)


# ── the page ──────────────────────────────────────────────────────────────────


def _empty(scope: ExposureScope, page: int, page_size: int) -> VulnerabilitiesResponse:
    return VulnerabilitiesResponse(
        enabled=scope.enabled,
        customer_codes=scope.customer_codes,
        agents_in_scope=len(scope.agents),
        severities=[SeverityCount(severity=level) for level in SEVERITIES],
        page=page,
        page_size=page_size,
        message="The Exposure page is not enabled for this customer" if not scope.enabled else "No agents to read",
    )


async def vulnerabilities(
    scope: ExposureScope,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> VulnerabilitiesResponse:
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    response = _empty(scope, page, page_size)
    if not scope.agents:
        return response
    try:
        answer = await indexer_search(overview_body(scope, severity, search, page, page_size))
        aggregations = answer.get("aggregations") or {}
        response.severities = parse_severities(aggregations)
        response.totals, ranked, response.total_cves = parse_page(aggregations)
        response.truncated = response.total_cves > CVE_RANK_LIMIT
        ids = [cve for cve, _, _ in ranked]
        details: Dict[str, dict] = {}
        if ids:
            details = parse_details((await indexer_search(details_body(scope, ids))).get("aggregations") or {})
    except Exception as e:
        logger.error(f"Customer portal exposure: vulnerabilities could not be read: {type(e).__name__}: {e}")
        response.error = READ_ERROR
        return response

    epss = await epss_scores(ids) if ids else {}
    response.cves = [
        CveRow(
            cve_id=cve,
            cvss=score,
            hosts=hosts,
            epss=epss.get(cve),
            severity=details.get(cve, {}).get("severity"),
            packages=details.get(cve, {}).get("packages", []),
            first_detected=details.get(cve, {}).get("first_detected"),
            published=details.get(cve, {}).get("published"),
        )
        for cve, score, hosts in ranked
    ]
    return response


async def cve_detail(scope: ExposureScope, cve_id: str) -> CveDetailResponse:
    """One CVE on the scope's agents. A CVE they do not have is an empty list, like any other."""
    if not scope.agents:
        return CveDetailResponse(cve_id=cve_id)
    try:
        hits = (await indexer_search(cve_body(scope, cve_id))).get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"Customer portal exposure: CVE {cve_id} could not be read: {type(e).__name__}: {e}")
        return CveDetailResponse(cve_id=cve_id, error=READ_ERROR)
    detail = parse_cve(cve_id, hits, scope)
    if detail.agents:
        detail.epss = (await epss_scores([cve_id])).get(cve_id)
    return detail


async def export_rows(scope: ExposureScope, severity: Optional[str], search: Optional[str]) -> Tuple[List[Tuple[dict, Any]], bool]:
    """The scope's findings under the filter, ``(source, owner)``, and whether EXPORT_LIMIT cut them."""
    owners = scope.by_agent()
    rows: List[Tuple[dict, Any]] = []
    async for hits in indexer_scroll(export_body(scope, severity, search)):
        for hit in hits:
            source = hit.get("_source") or {}
            owner = owners.get((str(_get(source, "agent.id") or ""), str(_get(source, "agent.name") or "")))
            if owner is None:
                continue
            if len(rows) >= EXPORT_LIMIT:
                return rows, True
            rows.append((source, owner))
    return rows, False


async def export_csv(scope: ExposureScope, severity: Optional[str], search: Optional[str]) -> Tuple[str, bool]:
    """The findings as CSV, one row per CVE × package × agent, and whether it was cut at EXPORT_LIMIT.

    An indexer that cannot be read is a 502 with the generic text: a file cannot carry an error.
    """
    try:
        rows, truncated = await export_rows(scope, severity, search) if scope.agents else ([], False)
    except Exception as e:
        logger.error(f"Customer portal exposure: export failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=READ_ERROR)
    rows.sort(
        key=lambda row: (
            SEVERITIES.index(_get(row[0], "vulnerability.severity")) if _get(row[0], "vulnerability.severity") in SEVERITIES else 9,
            str(_get(row[0], "vulnerability.id")),
            row[1].hostname,
        ),
    )
    epss = await epss_scores(_get(source, "vulnerability.id") for source, _ in rows) if rows else {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    for source, owner in rows:
        writer.writerow(csv_row(source, owner, epss))
    return output.getvalue(), truncated
