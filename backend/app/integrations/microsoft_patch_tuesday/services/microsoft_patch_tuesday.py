import datetime as dt
import json
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from loguru import logger

from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    AffectedProduct,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    AvailableCyclesResponse,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    CVSSInfo,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    EPSSInfo,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    KEVInfo,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdayItem,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdayRequest,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdayResponse,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdaySummary,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdaySummaryResponse,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PrioritizationInfo,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PriorityCounts,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    RemediationInfo,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    SourceInfo,
)

# Constants
MSRC_CVRF_BASE = "https://api.msrc.microsoft.com/cvrf/v3.0/cvrf"
EPSS_BASE = "https://api.first.org/data/v1/epss"
CISA_KEV_JSON = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def second_tuesday(year: int, month: int) -> dt.date:
    """Return date of the second Tuesday for a given year/month."""
    d = dt.date(year, month, 1)
    days_to_tuesday = (1 - d.weekday()) % 7
    first_tuesday = d + dt.timedelta(days=days_to_tuesday)
    return first_tuesday + dt.timedelta(days=7)


def get_default_cycle(today: Optional[dt.date] = None) -> str:
    """Default cycle is current month in 'YYYY-Mmm' format."""
    if today is None:
        today = dt.date.today()
    return f"{today.year}-{MONTH_ABBR[today.month - 1]}"


def parse_cycle(cycle: str) -> Tuple[int, int, str]:
    """
    Parse cycle in 'YYYY-Mmm' format.
    Returns (year, month_int, normalized_cycle).
    """
    m = re.fullmatch(r"(\d{4})-([A-Za-z]{3})", cycle.strip())
    if not m:
        raise ValueError("Cycle must be in format YYYY-Mmm (e.g., 2026-Jan)")
    year = int(m.group(1))
    mon = m.group(2).title()
    if mon not in MONTH_ABBR:
        raise ValueError(f"Invalid month abbreviation '{mon}'. Use one of: {', '.join(MONTH_ABBR)}")
    month = MONTH_ABBR.index(mon) + 1
    return year, month, f"{year}-{mon}"


def safe_float(x: Any) -> Optional[float]:
    """Safely convert a value to float."""
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def normalize_text(s: Any) -> Optional[str]:
    """Best-effort normalization to a single-line string."""
    if s is None:
        return None

    if isinstance(s, dict):
        for k in ("Value", "value", "Description", "description", "Text", "text", "Title", "title", "Name", "name"):
            if k in s and isinstance(s[k], (str, int, float)):
                s = s[k]
                break
        else:
            try:
                s = json.dumps(s, ensure_ascii=False)
            except Exception:
                s = str(s)

    if isinstance(s, list):
        parts = []
        for x in s:
            nx = normalize_text(x)
            if nx:
                parts.append(nx)
        s = " | ".join(parts)

    if not isinstance(s, str):
        s = str(s)

    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def product_family(name: Any) -> str:
    """Classify product into a coarse family bucket."""
    name_s = normalize_text(name) or ""
    n = name_s.lower()

    if "windows server" in n:
        return "Windows Server"
    if "windows" in n:
        return "Windows"
    if "office" in n or "microsoft 365" in n:
        return "Office/M365"
    if "exchange" in n:
        return "Exchange"
    if "sharepoint" in n:
        return "SharePoint"
    if "sql server" in n:
        return "SQL Server"
    if "visual studio" in n or ".net" in n:
        return "Developer Platform"
    if "edge" in n:
        return "Edge"
    if "azure" in n:
        return "Azure"
    if "dynamics" in n:
        return "Dynamics"
    return "Other"


def chunk_by_max_chars(items: List[str], max_chars: int = 1900) -> List[List[str]]:
    """Chunk items to keep URL parameter size under limits."""
    chunks: List[List[str]] = []
    current: List[str] = []
    current_len = 0
    for it in items:
        add_len = len(it) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            chunks.append(current)
            current = [it]
            current_len = len(it)
        else:
            current.append(it)
            current_len += add_len
    if current:
        chunks.append(current)
    return chunks


async def fetch_json(url: str, params: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    """Fetch JSON from a URL with proper error handling."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "CoPilot-PatchTuesday/1.0",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise RuntimeError(f"GET {url} failed: HTTP {response.status_code} - {response.text[:300]}")

        ctype = (response.headers.get("content-type") or "").lower()
        body = response.text.lstrip()
        if "application/json" not in ctype and body.startswith("<"):
            raise RuntimeError(
                f"Endpoint returned non-JSON (Content-Type: {ctype}). " "The MSRC API may have returned XML instead of JSON.",
            )

        try:
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Response was not valid JSON: {e}. First 300 chars: {response.text[:300]}") from e


async def fetch_epss_scores(cves: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch EPSS scores for a list of CVEs."""
    out: Dict[str, Dict[str, Any]] = {}
    cves = sorted(set([c.strip().upper() for c in cves if c and str(c).strip()]))

    if not cves:
        return out

    logger.info(f"Fetching EPSS scores for {len(cves)} CVEs")

    for chunk in chunk_by_max_chars(cves):
        try:
            params = {"cve": ",".join(chunk)}
            data = await fetch_json(EPSS_BASE, params=params)

            for row in data.get("data", []) or []:
                cve = (row.get("cve") or "").upper()
                if not cve:
                    continue
                out[cve] = {
                    "epss": safe_float(row.get("epss")),
                    "percentile": safe_float(row.get("percentile")),
                    "date": row.get("date"),
                }
        except Exception as e:
            logger.warning(f"Error fetching EPSS chunk: {e}")
            continue

    logger.info(f"Retrieved EPSS scores for {len(out)} CVEs")
    return out


async def fetch_kev_data() -> Dict[str, Dict[str, Any]]:
    """Fetch and parse CISA KEV data."""
    logger.info("Fetching CISA KEV data")

    try:
        kev_doc = await fetch_json(CISA_KEV_JSON)
    except Exception as e:
        logger.error(f"Failed to fetch KEV data: {e}")
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    vulns = kev_doc.get("vulnerabilities") or []
    if isinstance(vulns, dict):
        vulns = [vulns]

    for v in vulns:
        if not isinstance(v, dict):
            continue
        cve = (normalize_text(v.get("cveID") or v.get("cveId") or v.get("CVE")) or "").upper()
        if not cve.startswith("CVE-"):
            continue

        out[cve] = {
            "in_kev": True,
            "date_added": normalize_text(v.get("dateAdded")),
            "due_date": normalize_text(v.get("dueDate")),
            "required_action": normalize_text(v.get("requiredAction")),
            "known_ransomware_campaign_use": normalize_text(v.get("knownRansomwareCampaignUse")),
            "vendor_project": normalize_text(v.get("vendorProject")),
            "product": normalize_text(v.get("product")),
            "vulnerability_name": normalize_text(v.get("vulnerabilityName")),
            "short_description": normalize_text(v.get("shortDescription")),
            "notes": normalize_text(v.get("notes")),
        }

    logger.info(f"Loaded {len(out)} CVEs from CISA KEV")
    return out


def extract_cvss(vuln: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Extract CVSS score and vector from vulnerability data."""
    sets = vuln.get("CVSSScoreSets") or vuln.get("CvssScoreSets") or []
    if isinstance(sets, dict):
        sets = [sets]

    best_score = None
    best_vector = None

    for s in sets:
        if not isinstance(s, dict):
            continue
        score = safe_float(s.get("BaseScore") or s.get("baseScore") or s.get("Score"))
        vector = normalize_text(s.get("Vector") or s.get("vectorString") or s.get("VectorString"))
        if score is None:
            continue
        if best_score is None or score > best_score:
            best_score = score
            best_vector = vector

    return best_score, best_vector


def extract_severity(vuln: Dict[str, Any]) -> Optional[str]:
    """Extract severity from vulnerability data."""
    threats = vuln.get("Threats") or []
    if isinstance(threats, dict):
        threats = [threats]
    for t in threats:
        if not isinstance(t, dict):
            continue
        ttype = normalize_text(t.get("Type") or t.get("type") or "")
        desc = normalize_text(t.get("Description") or t.get("description"))
        if ttype and "severity" in ttype.lower() and desc:
            return desc.title()

    sev = normalize_text(vuln.get("Severity") or vuln.get("severity"))
    return sev.title() if sev else None


def extract_kbs(vuln: Dict[str, Any]) -> List[str]:
    """Extract KB article numbers from remediations."""
    kbs = set()
    rems = vuln.get("Remediations") or []
    if isinstance(rems, dict):
        rems = [rems]
    for r in rems:
        if not isinstance(r, dict):
            continue
        for field in ["Description", "URL", "Url", "description", "url"]:
            val = r.get(field)
            if not val:
                continue
            for kb in re.findall(r"\bKB\d{6,8}\b", str(val), flags=re.IGNORECASE):
                kbs.add(kb.upper())
    return sorted(kbs)


def build_product_lookup(doc: Dict[str, Any]) -> Dict[str, str]:
    """Build ProductID to product name lookup."""
    lookup: Dict[str, str] = {}

    pt = doc.get("ProductTree") or {}
    fp = pt.get("FullProductName") or []
    if isinstance(fp, dict):
        fp = [fp]

    for item in fp:
        if not isinstance(item, dict):
            continue
        pid = item.get("ProductID") or item.get("productId") or item.get("ProductId")
        val = normalize_text(item.get("Value") or item.get("value") or item.get("Name") or item.get("name"))
        if pid and val:
            lookup[str(pid)] = val

    return lookup


def extract_affected_products(vuln: Dict[str, Any], product_lookup: Dict[str, str]) -> List[str]:
    """Extract affected products from vulnerability data."""
    names = set()

    statuses = vuln.get("ProductStatuses") or vuln.get("ProductStatus") or []
    if isinstance(statuses, dict):
        statuses = [statuses]

    for st in statuses:
        if not isinstance(st, dict):
            continue
        for _, v in st.items():
            if isinstance(v, list):
                for pid in v:
                    pname = product_lookup.get(str(pid))
                    if pname:
                        names.add(pname)
            elif isinstance(v, (str, int)):
                pname = product_lookup.get(str(v))
                if pname:
                    names.add(pname)

    prods = vuln.get("Products")
    if isinstance(prods, list):
        for pid in prods:
            pname = product_lookup.get(str(pid))
            if pname:
                names.add(pname)

    return sorted(names)


def calculate_priority(
    severity: Optional[str],
    cvss: Optional[float],
    epss: Optional[float],
    family: str,
    in_kev: bool,
) -> Tuple[str, List[str], str]:
    """
    Calculate priority level (P0-P3) based on various factors.

    P0: CISA KEV, OR EPSS >= 0.9, OR (Critical and EPSS >= 0.7)
    P1: Critical OR (CVSS >= 8.0 and (EPSS >= 0.3 or core enterprise families))
    P2: Important/Moderate OR CVSS >= 6.0 OR EPSS >= 0.1
    P3: Otherwise
    """
    if in_kev:
        reasons = ["CISA KEV (known exploited)"]
        if epss is not None:
            reasons.append(f"EPSS={epss:.3f}")
        if cvss is not None:
            reasons.append(f"CVSS={cvss:.1f}")
        sla = "Emergency: known exploited. Patch/mitigate immediately; prioritize exposed and Tier-0 assets first."
        return "P0", reasons, sla

    reasons: List[str] = []
    sev = (severity or "").lower()
    e = epss if epss is not None else 0.0
    s = cvss if cvss is not None else 0.0

    core_families = {"Windows", "Windows Server", "Office/M365", "Exchange", "Edge"}

    if e >= 0.9 or (sev == "critical" and e >= 0.7):
        reasons += ["Very high EPSS" if e >= 0.9 else "Critical severity + high EPSS"]
        sla = "Emergency: validate mitigations immediately; deploy to highest-risk assets within 24h."
        return "P0", reasons, sla

    if sev == "critical":
        reasons.append("Critical severity")
    if s >= 8.0:
        reasons.append("High CVSS (>= 8.0)")
    if e >= 0.3:
        reasons.append("Elevated EPSS (>= 0.3)")
    if family in core_families:
        reasons.append(f"High enterprise footprint ({family})")

    if (sev == "critical") or (s >= 8.0 and (e >= 0.3 or family in core_families)):
        sla = "High: deploy to pilot in 24–48h; broad rollout in 72h."
        return "P1", reasons, sla

    if sev in {"important", "moderate"}:
        reasons.append(f"{severity.title() if severity else 'Unknown'} severity")
    if s >= 6.0:
        reasons.append("CVSS (>= 6.0)")
    if e >= 0.1:
        reasons.append("EPSS (>= 0.1)")

    if sev in {"important", "moderate"} or s >= 6.0 or e >= 0.1:
        sla = "Medium: deploy in the next standard patch window (7–14 days), sooner for exposed assets."
        return "P2", reasons, sla

    sla = "Low: patch in routine maintenance (30 days) unless asset criticality dictates otherwise."
    return "P3", reasons, sla


async def fetch_patch_tuesday_data(
    cycle: Optional[str] = None,
    include_epss: bool = True,
    include_kev: bool = True,
) -> Tuple[List[PatchTuesdayItem], PatchTuesdaySummary]:
    """
    Fetch and parse Patch Tuesday data for a given cycle.

    Args:
        cycle: Cycle in YYYY-Mmm format (e.g., 2026-Jan). Defaults to current month.
        include_epss: Whether to fetch and include EPSS scores.
        include_kev: Whether to fetch and include CISA KEV data.

    Returns:
        Tuple of (items, summary)
    """
    # Parse cycle
    if cycle:
        year, month, cycle_norm = parse_cycle(cycle)
    else:
        cycle_norm = get_default_cycle()
        year, month, cycle_norm = parse_cycle(cycle_norm)

    pt_date = second_tuesday(year, month)
    url = f"{MSRC_CVRF_BASE}/{cycle_norm}"

    logger.info(f"Fetching Patch Tuesday data for cycle {cycle_norm} (date: {pt_date.isoformat()})")

    # Fetch CVRF document
    doc = await fetch_json(url)

    # Build product lookup
    product_lookup = build_product_lookup(doc)

    # Parse vulnerabilities
    vulnerabilities = doc.get("Vulnerability") or doc.get("Vulnerabilities") or []
    if isinstance(vulnerabilities, dict):
        vulnerabilities = [vulnerabilities]

    # Collect all CVEs for enrichment
    cves_all: List[str] = []
    for v in vulnerabilities:
        if not isinstance(v, dict):
            continue
        cve = (normalize_text(v.get("CVE") or v.get("Cve") or v.get("cve")) or "").upper()
        if cve.startswith("CVE-"):
            cves_all.append(cve)

    # Fetch enrichment data
    epss_map: Dict[str, Dict[str, Any]] = {}
    kev_map: Dict[str, Dict[str, Any]] = {}

    if include_epss:
        epss_map = await fetch_epss_scores(cves_all)

    if include_kev:
        kev_map = await fetch_kev_data()

    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    items: List[PatchTuesdayItem] = []
    prio_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    family_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {}

    for v in vulnerabilities:
        if not isinstance(v, dict):
            continue

        cve = (normalize_text(v.get("CVE") or v.get("Cve") or v.get("cve")) or "").upper()
        if not cve.startswith("CVE-"):
            continue

        title = normalize_text(v.get("Title") or v.get("title"))
        severity = extract_severity(v)
        cvss_score, cvss_vector = extract_cvss(v)
        kbs = extract_kbs(v)

        affected_products = extract_affected_products(v, product_lookup)
        if not affected_products:
            affected_products = ["(Unknown product mapping)"]

        # Get enrichment data
        epss = epss_map.get(cve, {})
        epss_score = epss.get("epss")
        epss_pct = epss.get("percentile")
        epss_date = epss.get("date")

        kev = kev_map.get(cve, {"in_kev": False})
        in_kev = bool(kev.get("in_kev"))

        # Track severity counts
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for prod in affected_products:
            prod_norm = normalize_text(prod) or prod
            fam = product_family(prod_norm)
            family_counts[fam] = family_counts.get(fam, 0) + 1

            prio, reasons, sla = calculate_priority(severity, cvss_score, epss_score, fam, in_kev)
            prio_counts[prio] = prio_counts.get(prio, 0) + 1

            item = PatchTuesdayItem(
                cycle=cycle_norm,
                release_type="patch_tuesday",
                cve=cve,
                title=title,
                severity=severity,
                cvss=CVSSInfo(base=cvss_score, vector=cvss_vector),
                epss=EPSSInfo(score=epss_score, percentile=epss_pct, date=epss_date),
                kev=KEVInfo(
                    in_kev=in_kev,
                    date_added=kev.get("date_added"),
                    due_date=kev.get("due_date"),
                    required_action=kev.get("required_action"),
                    known_ransomware_campaign_use=kev.get("known_ransomware_campaign_use"),
                    vendor_project=kev.get("vendor_project"),
                    product=kev.get("product"),
                    vulnerability_name=kev.get("vulnerability_name"),
                    short_description=kev.get("short_description"),
                    notes=kev.get("notes"),
                ),
                affected=AffectedProduct(
                    product=prod_norm,
                    family=fam,
                    component_hint=title,
                ),
                remediation=RemediationInfo(kbs=kbs),
                prioritization=PrioritizationInfo(
                    priority=prio,
                    reason=reasons,
                    suggested_sla=sla,
                ),
                source=SourceInfo(
                    msrc_cvrf_id=cycle_norm,
                    msrc_cvrf_url=url,
                    cisa_kev_url=CISA_KEV_JSON,
                ),
                timestamp_utc=now_utc,
            )
            items.append(item)

    # Sort by priority, then EPSS desc, then CVSS desc
    prio_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(
        key=lambda r: (
            prio_rank.get(r.prioritization.priority, 9),
            -(r.epss.score or 0.0),
            -(r.cvss.base or 0.0),
            r.cve,
            r.affected.product,
        ),
    )

    summary = PatchTuesdaySummary(
        cycle=cycle_norm,
        patch_tuesday_date=pt_date.isoformat(),
        generated_utc=now_utc,
        unique_cves=len(set([x.cve for x in items])),
        total_records=len(items),
        by_priority=PriorityCounts(**prio_counts),
        by_family=dict(sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        by_severity=dict(sorted(severity_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
    )

    logger.info(f"Processed {summary.unique_cves} unique CVEs, {summary.total_records} total records for cycle {cycle_norm}")

    return items, summary


async def get_patch_tuesday(request: PatchTuesdayRequest) -> PatchTuesdayResponse:
    """
    Get full Patch Tuesday data for a cycle.

    Args:
        request: Request containing cycle and enrichment options.

    Returns:
        PatchTuesdayResponse with all items and summary.
    """
    try:
        items, summary = await fetch_patch_tuesday_data(
            cycle=request.cycle,
            include_epss=request.include_epss,
            include_kev=request.include_kev,
        )

        return PatchTuesdayResponse(
            success=True,
            message=f"Successfully retrieved {summary.unique_cves} CVEs for cycle {summary.cycle}",
            summary=summary,
            items=items,
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return PatchTuesdayResponse(
            success=False,
            message=str(e),
            summary=None,
            items=[],
        )
    except Exception as e:
        logger.error(f"Error fetching Patch Tuesday data: {e}")
        return PatchTuesdayResponse(
            success=False,
            message=f"Failed to fetch Patch Tuesday data: {e}",
            summary=None,
            items=[],
        )


async def get_patch_tuesday_summary(request: PatchTuesdayRequest, top_n: int = 25) -> PatchTuesdaySummaryResponse:
    """
    Get Patch Tuesday summary with top prioritized items.

    Args:
        request: Request containing cycle and enrichment options.
        top_n: Number of top items to include (default 25).

    Returns:
        PatchTuesdaySummaryResponse with summary and top items.
    """
    try:
        items, summary = await fetch_patch_tuesday_data(
            cycle=request.cycle,
            include_epss=request.include_epss,
            include_kev=request.include_kev,
        )

        return PatchTuesdaySummaryResponse(
            success=True,
            message=f"Successfully retrieved summary for cycle {summary.cycle}",
            summary=summary,
            top_items=items[:top_n],
        )
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return PatchTuesdaySummaryResponse(
            success=False,
            message=str(e),
            summary=None,
            top_items=[],
        )
    except Exception as e:
        logger.error(f"Error fetching Patch Tuesday summary: {e}")
        return PatchTuesdaySummaryResponse(
            success=False,
            message=f"Failed to fetch Patch Tuesday summary: {e}",
            summary=None,
            top_items=[],
        )


async def get_available_cycles() -> AvailableCyclesResponse:
    """
    Get available Patch Tuesday cycles.

    Returns recent cycles and information about the current/next Patch Tuesday.
    """
    try:
        today = dt.date.today()
        current_cycle = get_default_cycle(today)

        # Generate list of recent cycles (last 12 months)
        cycles = []
        for i in range(12):
            d = today - dt.timedelta(days=i * 30)
            cycle = get_default_cycle(d)
            if cycle not in cycles:
                cycles.append(cycle)

        # Calculate next Patch Tuesday
        year, month, _ = parse_cycle(current_cycle)
        pt_date = second_tuesday(year, month)

        if today > pt_date:
            # Move to next month
            if month == 12:
                next_year, next_month = year + 1, 1
            else:
                next_year, next_month = year, month + 1
            next_pt_date = second_tuesday(next_year, next_month)
        else:
            next_pt_date = pt_date

        return AvailableCyclesResponse(
            success=True,
            message="Successfully retrieved available cycles",
            cycles=cycles,
            current_cycle=current_cycle,
            next_patch_tuesday=next_pt_date.isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting available cycles: {e}")
        return AvailableCyclesResponse(
            success=False,
            message=f"Failed to get available cycles: {e}",
            cycles=[],
            current_cycle=get_default_cycle(),
            next_patch_tuesday="",
        )


async def search_cves_in_patch_tuesday(cve_ids: List[str], cycle: Optional[str] = None) -> PatchTuesdayResponse:
    """
    Search for specific CVEs in Patch Tuesday data.

    Args:
        cve_ids: List of CVE IDs to search for.
        cycle: Optional cycle to limit search to.

    Returns:
        PatchTuesdayResponse with matching items.
    """
    try:
        request = PatchTuesdayRequest(cycle=cycle)
        response = await get_patch_tuesday(request)

        if not response.success:
            return response

        # Filter items to only matching CVEs
        cve_set = set([c.upper() for c in cve_ids])
        matching_items = [item for item in response.items if item.cve.upper() in cve_set]

        # Recalculate summary for matched items
        if matching_items and response.summary:
            prio_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
            family_counts: Dict[str, int] = {}

            for item in matching_items:
                prio_counts[item.prioritization.priority] = prio_counts.get(item.prioritization.priority, 0) + 1
                family_counts[item.affected.family] = family_counts.get(item.affected.family, 0) + 1

            summary = PatchTuesdaySummary(
                cycle=response.summary.cycle,
                patch_tuesday_date=response.summary.patch_tuesday_date,
                generated_utc=response.summary.generated_utc,
                unique_cves=len(set([x.cve for x in matching_items])),
                total_records=len(matching_items),
                by_priority=PriorityCounts(**prio_counts),
                by_family=dict(sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
                by_severity=response.summary.by_severity,
            )
        else:
            summary = None

        return PatchTuesdayResponse(
            success=True,
            message=f"Found {len(matching_items)} items matching {len(cve_ids)} CVE(s)",
            summary=summary,
            items=matching_items,
        )
    except Exception as e:
        logger.error(f"Error searching CVEs: {e}")
        return PatchTuesdayResponse(
            success=False,
            message=f"Failed to search CVEs: {e}",
            summary=None,
            items=[],
        )
