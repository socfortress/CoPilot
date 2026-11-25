"""Indexer I/O of the weekly Sysmon noise statistics: field discovery, the labels, and one customer's two stages.

Every search takes the heavy-query slot shared with the firing-stats cache (one heavy search at a time across both),
has its own budget on both sides (the body's ``timeout`` 5 s short of the client's ``request_timeout``), and is cancelled
by its ``X-Opaque-Id`` when the client gives up. A search that timed out or lost shards is a failure, never a partial
report: undercounts are never sent. Events are attributed to a customer only by their customer label, matched
case-insensitively to a CoPilot customer code; an unlabelled event, or one whose label is no customer's, is never
attributed (no fallback to agent ids or host names).

Field discovery asks only about the indices that may hold the target week's events (``index_filter``), and the week's
searches go to exactly those indices: an old index that mapped a field differently neither hides the field nor fails
the searches' shards. An event whose key field still cannot be aggregated is left out, and said so: a warning, and the
report marked truncated.
"""
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from elasticsearch7.exceptions import AuthenticationException
from elasticsearch7.exceptions import AuthorizationException
from elasticsearch7.exceptions import ConnectionError as IndexerConnectionError
from elasticsearch7.exceptions import ConnectionTimeout
from loguru import logger

from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats.fields import BASE_FIELDS
from app.active_response.services.sysmon_stats.fields import EVENT_PLAN
from app.active_response.services.sysmon_stats.fields import FIELD_CAPS_FIELDS
from app.active_response.services.sysmon_stats.fields import FieldMap
from app.active_response.services.sysmon_stats.fields import discover
from app.active_response.services.sysmon_stats.queries import RawPattern
from app.active_response.services.sysmon_stats.queries import merge_shapes
from app.active_response.services.sysmon_stats.queries import parse_stage0
from app.active_response.services.sysmon_stats.queries import parse_stage1
from app.active_response.services.sysmon_stats.queries import parse_stage2
from app.active_response.services.sysmon_stats.queries import select_pairs
from app.active_response.services.sysmon_stats.queries import stage0_body
from app.active_response.services.sysmon_stats.queries import stage1_body
from app.active_response.services.sysmon_stats.queries import stage2_body
from app.connectors.wazuh_indexer.utils.heavy_query import heavy_query_slot

OPAQUE_PREFIX = "copilot-sysmon-stats-"


class IndexerTimeout(Exception):
    """A search timed out, on the indexer's side or the client's."""


class IndexerFailure(Exception):
    """A search failed (shards lost, a refused request): its counts cannot be trusted."""


class IndexerUnreachable(Exception):
    """The indexer cannot be reached or refuses CoPilot's credentials: no customer can be collected now."""


def week_bounds(monday: date) -> Tuple[int, int]:
    """[Monday 00:00 UTC, next Monday 00:00 UTC) in epoch milliseconds."""
    start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


async def _cancel_search(client: Any, opaque_id: str) -> None:
    """Cancel the search the client gave up on, found by its X-Opaque-Id. Best effort."""
    try:
        listing = await client.tasks.list(
            actions="indices:data/read/search",
            detailed=True,
            request_timeout=settings.METADATA_TIMEOUT_SECONDS,
        )
        for node in ((listing or {}).get("nodes") or {}).values():
            for task_id, task in ((node or {}).get("tasks") or {}).items():
                task_headers = (task or {}).get("headers") or {}
                if any(str(k).lower() == "x-opaque-id" and v == opaque_id for k, v in task_headers.items()):
                    await client.tasks.cancel(task_id=task_id, request_timeout=settings.METADATA_TIMEOUT_SECONDS)
                    logger.info(f"Sysmon stats: cancelled an abandoned indexer search ({task_id})")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Sysmon stats: could not cancel an abandoned indexer search ({type(exc).__name__})")


async def search(client: Any, index: str, body: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """One aggregation, in the heavy-query slot. Raises IndexerTimeout, IndexerFailure or IndexerUnreachable."""
    opaque_id = f"{OPAQUE_PREFIX}{uuid.uuid4().hex}"
    body = {**body, "timeout": f"{max(1, timeout - settings.SERVER_TIMEOUT_MARGIN_SECONDS)}s"}
    async with heavy_query_slot():
        try:
            response = await client.search(
                index=index,
                body=body,
                ignore_unavailable=True,
                allow_no_indices=True,
                request_timeout=timeout,
                opaque_id=opaque_id,
                request_cache=True,
            )
        except ConnectionTimeout:
            await _cancel_search(client, opaque_id)
            raise IndexerTimeout()
        except (AuthenticationException, AuthorizationException, IndexerConnectionError) as e:
            raise IndexerUnreachable(type(e).__name__)
        except Exception as e:  # noqa: BLE001 - a refused request: only its type is logged
            raise IndexerFailure(type(e).__name__)
    if not isinstance(response, dict):
        raise IndexerFailure("not an answer")
    if response.get("timed_out"):
        raise IndexerTimeout()
    shards = response.get("_shards") or {}
    if shards.get("failed"):
        raise IndexerFailure(f"{shards.get('failed')} shard(s) failed")
    return response


@dataclass
class Discovery:
    """The usable shapes, and the index expression the week's searches go to."""

    maps: List[FieldMap]
    index: str


async def _field_caps(client: Any, index: str, body: Optional[Dict[str, Any]]) -> Any:
    kwargs: Dict[str, Any] = {}
    if body is not None:
        kwargs["body"] = body
    try:
        return await client.field_caps(
            index=index,
            fields=FIELD_CAPS_FIELDS,
            ignore_unavailable=True,
            allow_no_indices=True,
            request_timeout=settings.METADATA_TIMEOUT_SECONDS,
            **kwargs,
        )
    except (AuthenticationException, AuthorizationException, IndexerConnectionError, ConnectionTimeout) as e:
        raise IndexerUnreachable(type(e).__name__)
    except Exception as e:  # noqa: BLE001
        raise IndexerFailure(type(e).__name__)


def _week_indices(response: Any) -> List[str]:
    indices = response.get("indices") if isinstance(response, dict) else None
    if not isinstance(indices, list):
        return []
    return sorted({i for i in indices if isinstance(i, str) and i and "," not in i and not any(ch.isspace() for ch in i)})


async def discover_fields(client: Any, index: str, monday: Optional[date] = None) -> Discovery:
    """The usable shapes. With ``monday``: asked of the indices that may hold that week's events only, which the week's
    searches then target by name; when the indexer cannot filter, names none or too many, the whole pattern is asked
    and searched (a field must then be aggregatable in every index of it)."""
    if monday is not None:
        start, end = week_bounds(monday)
        body = {"index_filter": {"range": {BASE_FIELDS["time"][0]: {"gte": start, "lt": end, "format": "epoch_millis"}}}}
        try:
            response = await _field_caps(client, index, body)
        except IndexerFailure as e:
            logger.info(f"Sysmon stats: the indexer could not limit field discovery to the week ({e}); asking every index")
        else:
            names = _week_indices(response)
            joined = ",".join(names)
            maps = discover(response)
            if names and maps and len(joined) <= settings.MAX_INDEX_PATTERN_LENGTH:
                return Discovery(maps=maps, index=joined)
    return Discovery(maps=discover(await _field_caps(client, index, None)), index=index)


@dataclass
class Labels:
    """Per customer code, the label spellings that are its own, per shape; and the codes that are ambiguous."""

    by_customer: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    ambiguous: Set[str] = field(default_factory=set)
    overflow: bool = False


def map_labels(labels_by_shape: Dict[str, Dict[str, int]], customer_codes: List[str]) -> Labels:
    """A label is a customer's when ``label.strip().lower() == code.lower()``. Two codes equal case-insensitively are
    ambiguous: neither gets any event."""
    folded: Dict[str, List[str]] = {}
    for code in customer_codes:
        folded.setdefault(code.strip().lower(), []).append(code)
    result = Labels()
    for codes in folded.values():
        if len(codes) > 1:
            result.ambiguous.update(codes)
    for shape, labels in labels_by_shape.items():
        for label in labels:
            codes = folded.get(label.strip().lower())
            if not codes or len(codes) != 1:
                continue
            result.by_customer.setdefault(codes[0], {}).setdefault(shape, []).append(label)
    return result


async def stage0(client: Any, index: str, maps: List[FieldMap], monday: date, timeout: int) -> Tuple[Dict[str, Dict[str, int]], bool]:
    start, end = week_bounds(monday)
    by_shape: Dict[str, Dict[str, int]] = {}
    overflow = False
    for fm in maps:
        labels, more = parse_stage0(await search(client, index, stage0_body(fm, start, end), timeout))
        by_shape[fm.shape] = labels
        overflow = overflow or more
    if overflow:
        logger.warning("Sysmon stats: more than 1000 customer labels in the week's Sysmon events; the rest are not reported")
    return by_shape, overflow


@dataclass
class Collection:
    """One customer's raw week: its report endpoints and leaves, before any redaction."""

    endpoints: int = 0
    patterns: List[RawPattern] = field(default_factory=list)
    pairs_left_out: bool = False
    cut_tails: List[int] = field(default_factory=list)
    # Event IDs with qualifying pairs whose patterns could not be collected (a key field not aggregatable)
    unavailable_events: List[int] = field(default_factory=list)
    # The customer's computers' names (the Windows event's Computer), to learn its host names and domains from
    computers: List[str] = field(default_factory=list)
    searches: int = 0


async def collect_customer(
    client: Any,
    index: str,
    maps: List[FieldMap],
    labels: Dict[str, List[str]],
    monday: date,
    level_max: int,
    min_endpoints: int,
    timeout: int,
) -> Collection:
    """Stage 1 and stage 2 for one customer, in every shape its labels appear in. Counts found in both shapes are never
    added (queries.merge_shapes): the same endpoints may be in both."""
    start, end = week_bounds(monday)
    result = Collection()
    raw: List[RawPattern] = []
    for fm in maps:
        shape_labels = labels.get(fm.shape)
        if not shape_labels:
            continue
        first = parse_stage1(await search(client, index, stage1_body(fm, shape_labels, start, end, level_max), timeout))
        result.searches += 1
        result.endpoints = max(result.endpoints, first.endpoints)
        result.cut_tails.extend(first.cut_tails)
        for name in first.computers:
            if name not in result.computers and len(result.computers) < settings.STAGE1_COMPUTERS_SIZE:
                result.computers.append(name)
        pairs, left_out = select_pairs(first.pairs, min_endpoints)
        result.pairs_left_out = result.pairs_left_out or left_out
        by_event: Dict[int, List[str]] = {}
        for pair in pairs:
            by_event.setdefault(pair.eid, []).append(pair.actor)
        for eid, actors in sorted(by_event.items()):
            if eid not in EVENT_PLAN:
                continue
            unmapped = fm.unmapped_keys(eid)
            if unmapped:
                if eid not in result.unavailable_events:
                    result.unavailable_events.append(eid)
                logger.warning(
                    f"Sysmon stats: event {eid} has patterns to report, but {', '.join(unmapped)} is not aggregatable in every "
                    f"index of the {fm.shape} shape; they are left out and the report is marked truncated",
                )
                continue
            body = stage2_body(fm, shape_labels, start, end, level_max, eid, actors)
            leaves, tails = parse_stage2(await search(client, index, body, timeout), eid)
            result.searches += 1
            raw.extend(leaves)
            result.cut_tails.extend(tails)
    result.patterns = merge_shapes(raw)
    result.endpoints = min(settings.MAX_REPORT_ENDPOINTS, result.endpoints)
    return result
