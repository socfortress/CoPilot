"""
Service layer for the Detection Catalog — a discovery surface over the same
rules already loaded by the CoPilot Searches feature.

Architecture notes:
- This is a **pure view layer**. It does NOT fetch anything from GitHub and
  does NOT maintain its own cache. It walks the in-memory ``rules_cache``
  populated by ``app.integrations.copilot_searches.services.copilot_searches``
  and aggregates differently per dimension (analytic_story, product,
  data_source, etc.).
- MITRE tactic names are resolved via the in-memory ``mitre_matrix`` populated
  by ``app.integrations.copilot_searches.services.mitre_coverage``. Same
  reasoning: no second fetch, single source of truth.
- Both backing caches load lazily on first access (``ensure_loaded``), and
  refresh of the CoPilot Searches cache is the single user-facing refresh
  path — there is no separate "refresh the catalog" action.
- All aggregation happens fresh on each request. The corpus is small enough
  (~500 rules) that walking it is sub-millisecond; a separate cache layer
  here would just create another invalidation surface.
"""

from collections import defaultdict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger

from app.integrations.copilot_searches.services.copilot_searches import rules_cache
from app.integrations.copilot_searches.services.mitre_coverage import mitre_matrix
from app.integrations.copilot_searches.services.wazuh_firing_stats_cache import (
    fetch_firing_stats_for_customer,
)
from app.integrations.copilot_searches.services.wazuh_firing_stats_cache import (
    wazuh_firing_stats_cache,
)
from app.integrations.copilot_searches.services.wazuh_rules_cache import (
    wazuh_rules_cache,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_list_of_str(value: Any) -> List[str]:
    """Return ``value`` as a list of strings, tolerating None / scalars / mixed lists."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _resolve_tactics_for_mitre_ids(mitre_ids: List[str]) -> List[str]:
    """
    Map a list of MITRE technique IDs (e.g. ``["T1059.007", "T1218"]``) to the
    unique set of tactic display names (e.g. ``["Execution", "Defense Evasion"]``).

    Uses the in-memory MITRE matrix; returns an empty list if the matrix isn't
    loaded yet (caller is expected to have invoked ``mitre_matrix.ensure_loaded``).
    """
    techniques = mitre_matrix.techniques
    tactics_by_short = {t["short_name"]: t["name"] for t in mitre_matrix.tactics}

    tactic_names: List[str] = []
    seen: set[str] = set()
    for raw in mitre_ids:
        if not isinstance(raw, str):
            continue
        # Match against the base technique (e.g. T1059.007 -> T1059); sub-techniques
        # carry their parent's tactic mapping in the STIX bundle.
        base = raw.split(".")[0].strip().upper()
        meta = techniques.get(base)
        if meta is None:
            continue
        for short_name in meta.get("tactic_short_names", []):
            display = tactics_by_short.get(short_name)
            if display and display not in seen:
                seen.add(display)
                tactic_names.append(display)
    return tactic_names


def _rule_mitre_ids(rule: Dict[str, Any]) -> List[str]:
    return _ensure_list_of_str(rule.get("tags", {}).get("mitre_attack_id"))


def _rule_stories(rule: Dict[str, Any]) -> List[str]:
    return _ensure_list_of_str(rule.get("tags", {}).get("analytic_story"))


def _rule_products(rule: Dict[str, Any]) -> List[str]:
    return _ensure_list_of_str(rule.get("tags", {}).get("product"))


def _rule_data_sources(rule: Dict[str, Any]) -> List[str]:
    return _ensure_list_of_str(rule.get("data_source"))


def _rule_max_date(rule: Dict[str, Any]) -> Optional[str]:
    date = rule.get("date")
    return date if isinstance(date, str) else None


def _newest(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Pick the later of two ISO date strings; None-tolerant."""
    if a is None:
        return b
    if b is None:
        return a
    return a if a >= b else b


# ---------------------------------------------------------------------------
# Stories index — table-of-stories landing
# ---------------------------------------------------------------------------


async def list_stories() -> List[Dict[str, Any]]:
    """
    Aggregate all rules into the set of unique analytic stories, with the
    per-story summary fields needed to render the index table:

        name | data_sources | tactics | products | date | detection_count

    Rules carrying multiple ``analytic_story`` tags contribute to every story
    they're tagged with (intentional — a single detection genuinely belongs
    to several stories in the published taxonomy).

    Rules with no ``analytic_story`` tag are silently excluded from the
    Stories surface. (They still appear in the Rules grid; the catalog is
    just a story-centric view.)
    """
    await rules_cache.ensure_loaded()
    await mitre_matrix.ensure_loaded()

    agg: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "data_sources": set(),
            "products": set(),
            "tactic_names": [],  # ordered, dedup'd
            "detection_count": 0,
            "date": None,
        },
    )

    for rule in rules_cache.get_all_rules():
        story_names = _rule_stories(rule)
        if not story_names:
            continue

        rule_tactics = _resolve_tactics_for_mitre_ids(_rule_mitre_ids(rule))
        rule_date = _rule_max_date(rule)

        for story_name in story_names:
            row = agg[story_name]
            row["data_sources"].update(_rule_data_sources(rule))
            row["products"].update(_rule_products(rule))
            for t in rule_tactics:
                if t not in row["tactic_names"]:
                    row["tactic_names"].append(t)
            row["detection_count"] += 1
            row["date"] = _newest(row["date"], rule_date)

    return [
        {
            "name": name,
            "data_sources": sorted(row["data_sources"]),
            "tactics": row["tactic_names"],
            "products": sorted(row["products"]),
            "date": row["date"],
            "detection_count": row["detection_count"],
        }
        for name, row in sorted(agg.items(), key=lambda kv: kv[0].lower())
    ]


# ---------------------------------------------------------------------------
# Single story detail
# ---------------------------------------------------------------------------


async def get_story_detail(story_name: str) -> Optional[Dict[str, Any]]:
    """
    Build the detail payload for one analytic story:

        - header metadata (id slug, author, latest version, latest date)
        - aggregated description (auto-generated from member detections)
        - detections table (one row per rule in the story)
        - data sources (deduplicated)
        - references (deduplicated)

    Returns ``None`` if no rule in the cache carries this story tag.
    """
    await rules_cache.ensure_loaded()
    await mitre_matrix.ensure_loaded()

    target = story_name.strip()
    members: List[Dict[str, Any]] = [rule for rule in rules_cache.get_all_rules() if target in _rule_stories(rule)]
    if not members:
        return None

    detections: List[Dict[str, Any]] = []
    data_sources: set[str] = set()
    references: List[str] = []
    references_seen: set[str] = set()
    products: set[str] = set()
    authors: set[str] = set()
    tactic_names: List[str] = []
    tactic_seen: set[str] = set()
    type_counts: Dict[str, int] = defaultdict(int)
    latest_date: Optional[str] = None
    latest_version: Optional[int] = None

    for rule in members:
        rule_tactics = _resolve_tactics_for_mitre_ids(_rule_mitre_ids(rule))
        for t in rule_tactics:
            if t not in tactic_seen:
                tactic_seen.add(t)
                tactic_names.append(t)

        rule_type = rule.get("type") or "Unknown"
        type_counts[rule_type] += 1

        detections.append(
            {
                "id": rule.get("id"),
                "name": rule.get("name", rule.get("id", "(unnamed)")),
                "type": rule_type,
                "severity": rule.get("response", {}).get("severity"),
                "mitre_attack_id": _rule_mitre_ids(rule),
                "tactics": rule_tactics,
                "description": rule.get("description"),
            },
        )

        data_sources.update(_rule_data_sources(rule))
        products.update(_rule_products(rule))
        author = rule.get("author")
        if isinstance(author, str) and author.strip():
            authors.add(author.strip())

        for ref in _ensure_list_of_str(rule.get("references")):
            if ref not in references_seen:
                references_seen.add(ref)
                references.append(ref)

        rule_date = _rule_max_date(rule)
        latest_date = _newest(latest_date, rule_date)

        version = rule.get("version")
        if isinstance(version, int):
            if latest_version is None or version > latest_version:
                latest_version = version

    detections.sort(key=lambda d: (d["name"] or "").lower())

    # Auto-generated "Why it matters" narrative — used until/unless a
    # curated story_metadata file is added in a sibling repo folder.
    type_summary = ", ".join(f"{count} {kind}" for kind, count in sorted(type_counts.items()))
    why_it_matters = (
        f"This story contains {len(detections)} detection(s) "
        f"covering {len(tactic_names)} MITRE ATT&CK tactic(s)"
        + (f" ({', '.join(tactic_names)})" if tactic_names else "")
        + ". "
        + (f"Detection types: {type_summary}. " if type_summary else "")
        + "Story metadata is auto-generated from member detections; curated narratives can be added later via a story-metadata file in the rule repo."
    )

    description = (
        f"{len(detections)} detection(s) tagged with the analytic story "
        f"'{target}'. Member detections span {len(tactic_names)} MITRE tactic(s)."
    )

    return {
        "name": target,
        "id": _story_slug(target),
        "description": description,
        "why_it_matters": why_it_matters,
        "detections": detections,
        "data_sources": sorted(data_sources),
        "tactics": tactic_names,
        "products": sorted(products),
        "authors": sorted(authors),
        "references": references,
        "date": latest_date,
        "version": latest_version,
        "detection_count": len(detections),
    }


def _story_slug(name: str) -> str:
    """A URL/display-safe slug for a story name. Stable per name."""
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name.strip().lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_") or "story"


# ---------------------------------------------------------------------------
# Catalog stats (for an Overview pane / facet counts)
# ---------------------------------------------------------------------------


async def get_catalog_stats() -> Dict[str, Any]:
    """
    Lightweight aggregation for the Catalog overview header — how many
    detections, stories, products, data sources we have indexed right now.
    Same in-memory walk pattern as ``list_stories``; cheap.

    Includes Wazuh-side counts so the header reflects the union of both
    corpora. Wazuh fields are returned as 0 / ``wazuh_available=false`` when
    the Wazuh Manager is unreachable rather than failing the whole call —
    the Stories tab must keep working even on Wazuh outages.
    """
    await rules_cache.ensure_loaded()
    await mitre_matrix.ensure_loaded()
    await wazuh_rules_cache.ensure_loaded()

    stories: set[str] = set()
    products: set[str] = set()
    data_sources: set[str] = set()
    tactic_names: set[str] = set()
    detection_count = 0

    for rule in rules_cache.get_all_rules():
        detection_count += 1
        stories.update(_rule_stories(rule))
        products.update(_rule_products(rule))
        data_sources.update(_rule_data_sources(rule))
        tactic_names.update(_resolve_tactics_for_mitre_ids(_rule_mitre_ids(rule)))

    return {
        "detection_count": detection_count,
        "story_count": len(stories),
        "product_count": len(products),
        "data_source_count": len(data_sources),
        "tactic_count": len(tactic_names),
        "last_refresh": rules_cache.last_refresh,
        # Wazuh-side counts — read-only mirror of the wazuh_rules_cache state.
        "wazuh_rule_count": wazuh_rules_cache.rules_count,
        "wazuh_last_refresh": wazuh_rules_cache.last_refresh,
        "wazuh_available": wazuh_rules_cache.is_available,
        "wazuh_unavailable_reason": wazuh_rules_cache.unavailable_reason,
    }


# ---------------------------------------------------------------------------
# Compliance pivot — group Wazuh rules by compliance framework control ID
# ---------------------------------------------------------------------------


# Frameworks we expose in the compliance pivot. Maps the API-friendly key
# (also the URL query value) to the human-readable label + the Wazuh
# rule-dict field name. Wazuh stores these as lists of control identifiers
# per rule. New frameworks: add a row here, no other code change needed.
COMPLIANCE_FRAMEWORKS: Dict[str, Dict[str, str]] = {
    "pci_dss": {"label": "PCI DSS", "field": "pci_dss"},
    "gdpr": {"label": "GDPR", "field": "gdpr"},
    "hipaa": {"label": "HIPAA", "field": "hipaa"},
    "nist_800_53": {"label": "NIST 800-53", "field": "nist_800_53"},
    "tsc": {"label": "TSC", "field": "tsc"},
    "gpg13": {"label": "GPG13", "field": "gpg13"},
}


def _rule_compliance_values(rule: Dict[str, Any], field: str) -> List[str]:
    """Pull and normalize a compliance-array field off a cached Wazuh rule."""
    raw = rule.get(field)
    if isinstance(raw, list):
        return [v for v in raw if isinstance(v, str) and v.strip()]
    if isinstance(raw, str):
        return [v.strip() for v in raw.split(",") if v.strip()]
    return []


async def list_compliance_pivot(framework: str) -> Dict[str, Any]:
    """
    Group every Wazuh rule by its values for the given compliance framework.

    Output shape:
        {
          "framework": "pci_dss",
          "framework_label": "PCI DSS",
          "groups": [
            {
              "control": "10.2.4",
              "rule_count": 23,
              "total_hits_30d": 487,
              "rule_ids": [5710, 5711, ...]
            },
            ...
          ],
          ...
        }

    Rules that don't carry ANY value for the framework field are excluded —
    "no compliance tag" isn't a group, it's just absence. The frontend can
    surface that count separately if useful, but for the pivot table itself
    we only list real controls.

    Groups are sorted by ``total_hits_30d`` descending, then by ``control``
    alphabetically — the "what's actively firing for PCI 10.2.4?" question
    is the most common analyst entry point.
    """
    framework_meta = COMPLIANCE_FRAMEWORKS.get(framework)
    if not framework_meta:
        raise ValueError(
            f"Unknown compliance framework {framework!r}. Valid: {list(COMPLIANCE_FRAMEWORKS)}",
        )

    await wazuh_rules_cache.ensure_loaded()
    await wazuh_firing_stats_cache.ensure_loaded()

    field = framework_meta["field"]

    # control_id -> {"rule_ids": [], "total_hits_30d": int}
    grouped: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"rule_ids": [], "total_hits_30d": 0, "total_hits_7d": 0},
    )
    rules_with_compliance = 0

    for raw_rule in wazuh_rules_cache.get_all_rules():
        controls = _rule_compliance_values(raw_rule, field)
        if not controls:
            continue
        rules_with_compliance += 1

        rid = raw_rule.get("id")
        stats = wazuh_firing_stats_cache.get(rid) if isinstance(rid, int) else {"hits_30d": 0, "hits_7d": 0}

        for control in controls:
            bucket = grouped[control]
            if isinstance(rid, int):
                bucket["rule_ids"].append(rid)
            bucket["total_hits_30d"] += stats["hits_30d"]
            bucket["total_hits_7d"] += stats["hits_7d"]

    groups = [
        {
            "control": control,
            "rule_count": len(bucket["rule_ids"]),
            "rule_ids": sorted(bucket["rule_ids"]),
            "total_hits_30d": bucket["total_hits_30d"],
            "total_hits_7d": bucket["total_hits_7d"],
        }
        for control, bucket in grouped.items()
    ]
    # Most-noisy-controls first; ties broken by control ID alphabetical so
    # the order is stable across calls.
    groups.sort(key=lambda g: (-g["total_hits_30d"], g["control"]))

    return {
        "framework": framework,
        "framework_label": framework_meta["label"],
        "groups": groups,
        "control_count": len(groups),
        "rules_with_compliance": rules_with_compliance,
        "total_rules": len(wazuh_rules_cache.get_all_rules()),
        "firing_stats_available": wazuh_firing_stats_cache.is_available,
    }


def list_compliance_frameworks() -> List[Dict[str, str]]:
    """List the frameworks the compliance pivot supports. Drives the UI selector."""
    return [{"key": key, "label": meta["label"]} for key, meta in COMPLIANCE_FRAMEWORKS.items()]


# ---------------------------------------------------------------------------
# Logtest — "which rule would match this log line?"
# ---------------------------------------------------------------------------


async def run_log_test(
    event: str,
    log_format: str = "syslog",
    location: str = "logtest",
) -> Dict[str, Any]:
    """
    Wrapper that runs Wazuh's logtest and decorates the result with details
    the catalog already has cached (so the UI gets one consistent rule
    shape regardless of whether it's reading from the index table, the
    detail modal, or a logtest match).

    Returns a dict the route can serialize directly:
        - ``matched``: bool
        - ``rule_id``, ``description``, ``level``, ``groups``, ``mitre``,
          ``tactics``: from the logtest output, enriched with the catalog's
          mitre_matrix-resolved tactic display names when we have them
        - ``alert``: the full Wazuh alert envelope (decoder/predecoder/data)
        - ``unavailable_reason``: filled when the logtest call itself failed
          so the UI can show an inline error
    """
    from app.connectors.wazuh_manager.services.logtest import run_logtest

    await mitre_matrix.ensure_loaded()

    try:
        result = await run_logtest(event=event, log_format=log_format, location=location)
    except Exception as exc:  # noqa: BLE001
        # Service exceptions are converted to a structured "unavailable"
        # response rather than re-raised — the catalog should feel like a
        # stable surface; the route wraps real HTTPException for input-
        # validation errors but transport hiccups are reported inline.
        logger.warning(f"Logtest failed: {exc}")
        return {
            "matched": False,
            "rule": None,
            "alert": None,
            "tactics": [],
            "unavailable_reason": str(exc),
        }

    tactics: List[str] = []
    rule = result.get("rule")
    if rule:
        # Enrich with resolved tactic display names using the catalog's
        # mitre_matrix — Wazuh only emits T-IDs; we want analyst-readable
        # tactic names too so the result panel matches the rest of the catalog.
        tactics = _resolve_tactics_for_mitre_ids(rule.get("mitre") or [])

    return {
        "matched": result["matched"],
        "rule": rule,
        "alert": result.get("alert"),
        "tactics": tactics,
        "unavailable_reason": None,
    }


# ---------------------------------------------------------------------------
# Coverage Gaps — MITRE techniques unaddressed by either rule corpus
# ---------------------------------------------------------------------------


async def list_coverage_gaps() -> Dict[str, Any]:
    """
    Return every MITRE ATT&CK technique that is NOT covered by any rule in
    the CoPilot Searches corpus OR the Wazuh ruleset.

    A technique is "covered" if at least one rule (from either source)
    declares its T-ID or any sub-technique thereof. We normalize to base
    technique IDs (``T1059.007 → T1059``) so a sub-technique counts as
    coverage for its parent — same convention used elsewhere in this file
    when resolving tactics for a rule.

    Output is sorted by technique ID so the UI list is stable across loads.
    Sub-techniques are deliberately collapsed into their parents — analysts
    care about "do we have anything for PowerShell (T1059)?" not "do we
    have anything for T1059.001 specifically?". Listing every sub-technique
    individually would flood the gap report with thousands of rows.
    """
    await rules_cache.ensure_loaded()
    await mitre_matrix.ensure_loaded()
    await wazuh_rules_cache.ensure_loaded()

    # Collect the set of covered base-technique IDs across both corpora.
    covered_ids: set[str] = set()
    for rule in rules_cache.get_all_rules():
        for tid in _rule_mitre_ids(rule):
            base = tid.split(".")[0].strip().upper()
            if base:
                covered_ids.add(base)
    for rule in wazuh_rules_cache.get_all_rules():
        for tid in _wazuh_mitre_ids(rule):
            base = tid.split(".")[0].strip().upper()
            if base:
                covered_ids.add(base)

    techniques = mitre_matrix.techniques
    tactics_by_short = {t["short_name"]: t["name"] for t in mitre_matrix.tactics}

    gaps: List[Dict[str, Any]] = []
    base_technique_count = 0
    for tid, meta in techniques.items():
        # Skip sub-techniques in the gap list — see docstring rationale.
        if meta.get("is_subtechnique"):
            continue
        base_technique_count += 1
        if tid in covered_ids:
            continue

        tactic_names: List[str] = []
        for short in meta.get("tactic_short_names", []):
            display = tactics_by_short.get(short)
            if display and display not in tactic_names:
                tactic_names.append(display)

        gaps.append(
            {
                "technique_id": tid,
                "technique_name": meta.get("name", tid),
                "tactics": tactic_names,
                "url": meta.get("url"),
            },
        )

    gaps.sort(key=lambda g: g["technique_id"])

    covered_count = base_technique_count - len(gaps)
    coverage_pct = (covered_count / base_technique_count * 100) if base_technique_count else 0.0

    return {
        "gaps": gaps,
        "gap_count": len(gaps),
        "covered_count": covered_count,
        "total_techniques": base_technique_count,
        "coverage_pct": round(coverage_pct, 1),
    }


async def get_coverage_gap(technique_id: str) -> Dict[str, Any] | None:
    payload = await list_coverage_gaps()
    tid = technique_id.strip().upper()
    for gap in payload["gaps"]:
        if gap["technique_id"].upper() == tid:
            return gap
    return None


# ---------------------------------------------------------------------------
# Wazuh Rules tab — list + single-rule detail
# ---------------------------------------------------------------------------


def _wazuh_groups(rule: Dict[str, Any]) -> List[str]:
    """
    Wazuh's ``groups`` field is already a list in the schema but Wazuh
    occasionally returns it as a comma-joined string. Tolerate both.
    """
    raw = rule.get("groups")
    if isinstance(raw, list):
        return [g for g in raw if isinstance(g, str) and g.strip()]
    if isinstance(raw, str):
        return [g.strip() for g in raw.split(",") if g.strip()]
    return []


def _wazuh_mitre_ids(rule: Dict[str, Any]) -> List[str]:
    """
    Same tolerance as ``_wazuh_groups`` — Wazuh's ``mitre`` field is sometimes
    a list of T-IDs, sometimes a single string. Normalize.
    """
    raw = rule.get("mitre")
    if isinstance(raw, list):
        return [m for m in raw if isinstance(m, str) and m.strip()]
    if isinstance(raw, str):
        return [m.strip() for m in raw.split(",") if m.strip()]
    return []


def _wazuh_compliance(rule: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Group all compliance-framework arrays into one nested dict so the UI can
    render them as labelled chip groups without hard-coding the framework
    list in the frontend.
    """
    return {
        "pci_dss": _ensure_list_of_str(rule.get("pci_dss")),
        "gdpr": _ensure_list_of_str(rule.get("gdpr")),
        "hipaa": _ensure_list_of_str(rule.get("hipaa")),
        "nist_800_53": _ensure_list_of_str(rule.get("nist_800_53")),
        "tsc": _ensure_list_of_str(rule.get("tsc")),
        "gpg13": _ensure_list_of_str(rule.get("gpg13")),
    }


def _wazuh_row(rule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Project a cached Wazuh rule down to the columns the index table renders.

    Firing counts come from ``wazuh_firing_stats_cache`` if available — a
    missing entry means "0 hits in the 30d window", not "no data". The cache's
    own ``is_available`` flag (mirrored on the list envelope as
    ``firing_stats_available``) is what tells the UI whether to render the
    Hits column at all vs. hiding it because we can't tell.
    """
    rid = rule.get("id")
    stats = wazuh_firing_stats_cache.get(rid) if isinstance(rid, int) else {"hits_30d": 0, "hits_7d": 0, "last_seen": None}
    return {
        "id": rid,
        "level": rule.get("level"),
        "status": rule.get("status"),
        "description": rule.get("description") or "",
        "filename": rule.get("filename") or "",
        "relative_dirname": rule.get("relative_dirname") or "",
        "groups": _wazuh_groups(rule),
        "mitre": _wazuh_mitre_ids(rule),
        "hits_7d": stats["hits_7d"],
        "hits_30d": stats["hits_30d"],
        "last_seen": stats.get("last_seen"),
    }


async def list_wazuh_rules(customer_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Return the full cached Wazuh ruleset projected to the index-table shape.

    Returns the whole corpus in one shot (typical Wazuh install ships ~3–5k
    rules, ~3–5 MB JSON). Filtering and pagination happen client-side in the
    same pattern as the Stories index — keeps the API simple and the UX
    responsive (no round-trip per filter keystroke).

    When ``customer_code`` is set, firing counts (hits_7d / hits_30d /
    last_seen) are scoped to that customer's alerts via a fresh ES query
    (not cached — see ``fetch_firing_stats_for_customer`` for rationale).
    The rule list itself is the same — every rule is shown — but the hit
    columns reflect "what's been firing for THIS customer." Rules without
    any hits for the customer get zeros.

    Always returns a populated envelope. When Wazuh is unavailable, ``rules``
    is empty and ``available=False`` + ``unavailable_reason`` carries the
    explanation so the frontend can render an inline empty state.
    """
    await wazuh_rules_cache.ensure_loaded()
    # Load firing stats too — they're cached separately with their own TTL,
    # so this is cheap. _wazuh_row reads from the firing-stats cache below.
    await wazuh_firing_stats_cache.ensure_loaded()

    # Per-customer override: fetch a fresh per-customer aggregation and
    # splice it into each row in place of the global stats. We don't mutate
    # the row builder — instead build rows with global stats, then patch the
    # firing fields. Keeps _wazuh_row's semantics clean and isolated.
    customer_stats: Dict[int, Dict[str, Any]] = {}
    if customer_code:
        customer_stats = await fetch_firing_stats_for_customer(customer_code)

    rows: List[Dict[str, Any]] = []
    for raw in wazuh_rules_cache.get_all_rules():
        row = _wazuh_row(raw)
        if customer_code:
            # Override stats with the per-customer numbers. Missing rule_id
            # in customer_stats means "this rule hasn't fired for this
            # customer" — zero everything out rather than leaving the global
            # numbers in place, which would be misleading.
            rid = row.get("id")
            cstats = customer_stats.get(rid) if isinstance(rid, int) else None
            if cstats:
                row["hits_7d"] = cstats["hits_7d"]
                row["hits_30d"] = cstats["hits_30d"]
                row["last_seen"] = cstats.get("last_seen")
            else:
                row["hits_7d"] = 0
                row["hits_30d"] = 0
                row["last_seen"] = None
        rows.append(row)

    # Sort by integer ID for a stable, intuitive default order — operators
    # think of Wazuh rules numerically.
    rows.sort(key=lambda r: r["id"] if isinstance(r["id"], int) else 0)

    return {
        "rules": rows,
        "total": len(rows),
        "available": wazuh_rules_cache.is_available,
        "unavailable_reason": wazuh_rules_cache.unavailable_reason,
        "last_refresh": wazuh_rules_cache.last_refresh,
        # Firing-stats availability mirrored on the envelope so the UI knows
        # whether to render the Hits column (no point showing "0" for every
        # row when the indexer isn't reachable — that'd be misleading).
        "firing_stats_available": wazuh_firing_stats_cache.is_available,
        "firing_stats_unavailable_reason": wazuh_firing_stats_cache.unavailable_reason,
        "firing_stats_last_refresh": wazuh_firing_stats_cache.last_refresh,
        # Echoes the request so the UI can confirm the scope it's showing.
        # Empty string when the global view is being served.
        "customer_code": customer_code or "",
    }


async def get_wazuh_rule_detail(rule_id: int) -> Optional[Dict[str, Any]]:
    """
    Build the full meta payload for a single Wazuh rule — fed into the detail
    modal. Returns ``None`` when the cache doesn't know that ID (caller maps
    that to 404).

    No second Wazuh API call: everything the UI needs is already on the cached
    list response. The ``details`` field carries the if-then logic (if_sid,
    match, regex, decoded_as, …) which the modal pretty-prints as chips, and
    ``source_xml`` is a reconstructed ``<rule>`` block the modal renders as a
    code snippet — analysts asked to "see how the rule is written" without
    the auth and parsing overhead of fetching the original ``.xml`` file.
    """
    await wazuh_rules_cache.ensure_loaded()
    await mitre_matrix.ensure_loaded()
    await wazuh_firing_stats_cache.ensure_loaded()

    rule = wazuh_rules_cache.get_rule(rule_id)
    if rule is None:
        return None

    mitre_ids = _wazuh_mitre_ids(rule)
    tactic_names = _resolve_tactics_for_mitre_ids(mitre_ids)
    stats = wazuh_firing_stats_cache.get(rule_id)

    return {
        "id": rule.get("id"),
        "level": rule.get("level"),
        "status": rule.get("status"),
        "description": rule.get("description") or "",
        "filename": rule.get("filename") or "",
        "relative_dirname": rule.get("relative_dirname") or "",
        "groups": _wazuh_groups(rule),
        "mitre": mitre_ids,
        "tactics": tactic_names,  # resolved via mitre_matrix for richer display
        "compliance": _wazuh_compliance(rule),
        # The if/then logic dict, pretty-printed by the modal as labelled
        # rows. Passed through as-is so the UI can iterate any keys Wazuh
        # decides to emit (we don't want to hard-code the field list).
        "details": rule.get("details") or {},
        # Reconstructed XML for the "Rule Source" section. See
        # _synthesize_rule_xml below for the why-not-fetch-the-file rationale.
        "source_xml": _synthesize_rule_xml(rule),
        # Firing counts from the indexer. ``firing_stats_available`` mirrors
        # the cache state — the modal hides the hits panel entirely when
        # we can't pull stats (don't show "0 hits" when we really mean
        # "indexer unreachable, no idea").
        "hits_7d": stats["hits_7d"],
        "hits_30d": stats["hits_30d"],
        "last_seen": stats.get("last_seen"),
        "firing_stats_available": wazuh_firing_stats_cache.is_available,
        "firing_stats_unavailable_reason": wazuh_firing_stats_cache.unavailable_reason,
    }


# ---------------------------------------------------------------------------
# Rule source XML synthesis
# ---------------------------------------------------------------------------


def _synthesize_rule_xml(rule: Dict[str, Any]) -> str:
    """
    Reconstruct the ``<rule>`` XML block for a Wazuh rule from its cached
    metadata.

    Why synthesize instead of fetching the original file via Wazuh's
    ``GET /rules/files/{filename}``:

    - That endpoint returns the **whole file** — a single .xml file routinely
      contains dozens of rules wrapped in ``<group>`` blocks. We'd have to
      parse it and extract just the rule with the matching ``id``, which
      adds an XML-parsing dependency and a second network round-trip.
    - The original file endpoint is also admin-scoped. Proxying it through
      the catalog (which is admin|analyst|customer_user) means an extra
      route, extra schema, and extra service plumbing for what amounts to
      formatting.
    - Every field we'd need to fill the XML is already on the cached rule —
      ``id``, ``level``, ``description``, ``groups``, ``mitre``, compliance
      arrays, and the free-form ``details`` dict carrying the if-then logic.

    The result is functionally identical to what an analyst would see if they
    cracked open the source ``.xml`` file: a clean ``<rule id="…" level="…">``
    block with the same children. It may not be byte-identical (comments,
    original whitespace, attribute order) — if anyone needs the exact source
    later we can layer a "View raw file" button on top of a future
    ``/catalog/wazuh-rules/{id}/source`` endpoint.
    """
    rid = rule.get("id")
    level = rule.get("level")
    # Header attributes — id + level only. Wazuh's other rule attributes
    # (frequency, timeframe, maxsize, …) live under ``details`` and are
    # rendered as child elements below for consistency.
    header_parts = [f'id="{rid}"' if rid is not None else None, f'level="{level}"' if level is not None else None]
    header = " ".join(p for p in header_parts if p)

    lines: List[str] = [f"<rule {header}>" if header else "<rule>"]

    # Children. Order tries to match what hand-written Wazuh rule files look
    # like in practice: decoded_as → description → group → if-then logic →
    # mitre → compliance. The exact order isn't load-bearing but it keeps
    # the output readable.
    details = rule.get("details") or {}

    # decoded_as is conventionally near the top.
    if "decoded_as" in details:
        lines.append(f"  <decoded_as>{_xml_escape(_stringify_detail_value(details['decoded_as']))}</decoded_as>")

    description = rule.get("description")
    if description:
        lines.append(f"  <description>{_xml_escape(description)}</description>")

    # Groups are stored as a list in the cache; Wazuh's file convention is a
    # single ``<group>`` with comma-separated values (trailing comma included).
    groups = _wazuh_groups(rule)
    if groups:
        joined = ",".join(groups) + ","
        lines.append(f"  <group>{_xml_escape(joined)}</group>")

    # Remaining details — anything we haven't already rendered above. We
    # iterate whatever keys Wazuh emits so new fields appear automatically.
    rendered_keys = {"decoded_as"}
    for key, value in details.items():
        if key in rendered_keys:
            continue
        lines.append(_render_detail_element(key, value))

    # MITRE — Wazuh's convention is a single <mitre> wrapper with <id>
    # children per technique.
    mitre_ids = _wazuh_mitre_ids(rule)
    if mitre_ids:
        lines.append("  <mitre>")
        for mid in mitre_ids:
            lines.append(f"    <id>{_xml_escape(mid)}</id>")
        lines.append("  </mitre>")

    # Compliance arrays — one element per value, matching Wazuh's source
    # format (multiple <pci_dss>X.Y.Z</pci_dss> rather than a list).
    compliance = _wazuh_compliance(rule)
    for framework_key, values in compliance.items():
        for v in values:
            # Use the schema key verbatim except for the NIST renaming, which
            # uses the hyphenated form in source files.
            tag = "nist-800-53" if framework_key == "nist_800_53" else framework_key
            lines.append(f"  <{tag}>{_xml_escape(v)}</{tag}>")

    lines.append("</rule>")
    return "\n".join(lines)


def _render_detail_element(key: str, value: Any) -> str:
    """
    Render one ``details`` entry as an XML child element.

    Wazuh's API returns mixed shapes for these. A few cases worth handling:

    - **String** → ``<key>value</key>``. The common case (if_sid, regex, …).
    - **Dict with a "pattern" key** → ``<key>pattern_value</key>``. Wazuh's
      API sometimes wraps match/regex values in ``{"pattern": "…"}``; the
      analyst-facing XML just shows the text content.
    - **Dict with other keys** → treat the dict as attributes + a possible
      text body. Mirrors Wazuh's ``<match type="pcre2">…</match>`` shape.
    - **List** → emit one element per item (e.g. multiple ``<match>`` lines).
    - **Anything else** → JSON-encode as the text body. Last-resort fallback
      so we don't silently drop unknown shapes.
    """
    if isinstance(value, list):
        # One element per list entry, recursively rendered.
        return "\n".join(_render_detail_element(key, item) for item in value)

    if isinstance(value, dict):
        # The "pattern" wrapper case — flatten to text content.
        if set(value.keys()) == {"pattern"}:
            return f"  <{key}>{_xml_escape(_stringify_detail_value(value['pattern']))}</{key}>"
        # Mixed dict — pull out any text-ish key as the body, treat the rest
        # as attributes. This is a heuristic; Wazuh's exact shape varies.
        text_keys = {"pattern", "value", "text", "#text"}
        attrs: Dict[str, Any] = {}
        body: Optional[str] = None
        for k, v in value.items():
            if k in text_keys and body is None:
                body = _stringify_detail_value(v)
            else:
                attrs[k] = v
        attr_str = "".join(f' {ak}="{_xml_escape(str(av))}"' for ak, av in attrs.items())
        if body is not None:
            return f"  <{key}{attr_str}>{_xml_escape(body)}</{key}>"
        return f"  <{key}{attr_str} />"

    # Scalar — string, number, bool, None.
    text = _stringify_detail_value(value)
    if text == "":
        return f"  <{key} />"
    return f"  <{key}>{_xml_escape(text)}</{key}>"


def _stringify_detail_value(value: Any) -> str:
    """Best-effort scalar-to-string. JSON-encodes complex values."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    # Last resort — render unknown shapes as compact JSON rather than
    # Python's repr (which would emit single quotes and 'True'/'None').
    try:
        import json

        return json.dumps(value, separators=(",", ":"))
    except Exception:
        return str(value)


def _xml_escape(text: str) -> str:
    """
    Minimal XML escaping for the five reserved characters. We don't use
    ``xml.sax.saxutils.escape`` because we need to handle ``"`` and ``'`` as
    well (they appear inside attribute values, and we use both quote styles
    in synthesized output).
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
