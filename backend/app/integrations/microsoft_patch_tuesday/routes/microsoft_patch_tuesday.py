from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Query
from loguru import logger

from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    AvailableCyclesResponse,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdayRequest,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdayResponse,
)
from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
    PatchTuesdaySummaryResponse,
)
from app.integrations.microsoft_patch_tuesday.services.microsoft_patch_tuesday import (
    get_available_cycles,
)
from app.integrations.microsoft_patch_tuesday.services.microsoft_patch_tuesday import (
    get_patch_tuesday,
)
from app.integrations.microsoft_patch_tuesday.services.microsoft_patch_tuesday import (
    get_patch_tuesday_summary,
)
from app.integrations.microsoft_patch_tuesday.services.microsoft_patch_tuesday import (
    search_cves_in_patch_tuesday,
)

microsoft_patch_tuesday_router = APIRouter()


@microsoft_patch_tuesday_router.get(
    "",
    response_model=PatchTuesdayResponse,
    description="Get full Patch Tuesday data for a specific cycle",
)
async def get_patch_tuesday_data(
    cycle: Optional[str] = Query(
        None,
        description="Cycle in YYYY-Mmm format (e.g., 2026-Jan). Defaults to current month.",
        regex=r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$",
    ),
    include_epss: bool = Query(True, description="Include EPSS scores in the response"),
    include_kev: bool = Query(True, description="Include CISA KEV data in the response"),
) -> PatchTuesdayResponse:
    """
    Get full Patch Tuesday vulnerability data for a specific cycle.

    This endpoint fetches data from the Microsoft Security Response Center (MSRC) CVRF API,
    enriches it with EPSS scores and CISA KEV information, and returns prioritized results.

    **Priority Levels:**
    - **P0 (Emergency)**: Known exploited (CISA KEV), very high EPSS (>=0.9), or Critical + high EPSS
    - **P1 (High)**: Critical severity, or high CVSS (>=8.0) with elevated EPSS or core enterprise products
    - **P2 (Medium)**: Important/Moderate severity, CVSS >=6.0, or EPSS >=0.1
    - **P3 (Low)**: All other vulnerabilities

    **Product Families:**
    - Windows, Windows Server, Office/M365, Exchange, SharePoint, SQL Server,
      Developer Platform, Edge, Azure, Dynamics, Other
    """
    logger.info(f"Fetching Patch Tuesday data for cycle: {cycle or 'current'}")

    request = PatchTuesdayRequest(
        cycle=cycle,
        include_epss=include_epss,
        include_kev=include_kev,
    )

    return await get_patch_tuesday(request)


@microsoft_patch_tuesday_router.get(
    "/summary",
    response_model=PatchTuesdaySummaryResponse,
    description="Get Patch Tuesday summary with top prioritized items",
)
async def get_patch_tuesday_summary_endpoint(
    cycle: Optional[str] = Query(
        None,
        description="Cycle in YYYY-Mmm format (e.g., 2026-Jan). Defaults to current month.",
        regex=r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$",
    ),
    include_epss: bool = Query(True, description="Include EPSS scores in the response"),
    include_kev: bool = Query(True, description="Include CISA KEV data in the response"),
    top_n: int = Query(25, ge=1, le=100, description="Number of top items to include"),
) -> PatchTuesdaySummaryResponse:
    """
    Get Patch Tuesday summary with top prioritized vulnerabilities.

    This is a lighter endpoint that returns only the summary statistics and
    top N prioritized items, suitable for dashboards and quick overviews.
    """
    logger.info(f"Fetching Patch Tuesday summary for cycle: {cycle or 'current'}")

    request = PatchTuesdayRequest(
        cycle=cycle,
        include_epss=include_epss,
        include_kev=include_kev,
    )

    return await get_patch_tuesday_summary(request, top_n=top_n)


@microsoft_patch_tuesday_router.get(
    "/cycles",
    response_model=AvailableCyclesResponse,
    description="Get available Patch Tuesday cycles",
)
async def get_cycles() -> AvailableCyclesResponse:
    """
    Get available Patch Tuesday cycles.

    Returns a list of recent cycles (last 12 months), the current cycle,
    and the date of the next Patch Tuesday.
    """
    logger.info("Fetching available Patch Tuesday cycles")
    return await get_available_cycles()


@microsoft_patch_tuesday_router.get(
    "/search",
    response_model=PatchTuesdayResponse,
    description="Search for specific CVEs in Patch Tuesday data",
)
async def search_cves(
    cve_ids: List[str] = Query(..., description="List of CVE IDs to search for"),
    cycle: Optional[str] = Query(
        None,
        description="Cycle in YYYY-Mmm format to limit search to. Defaults to current month.",
        regex=r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$",
    ),
) -> PatchTuesdayResponse:
    """
    Search for specific CVEs in Patch Tuesday data.

    Returns detailed information about the specified CVEs including
    EPSS scores, CISA KEV status, and prioritization recommendations.
    """
    logger.info(f"Searching for CVEs: {cve_ids} in cycle: {cycle or 'current'}")
    return await search_cves_in_patch_tuesday(cve_ids, cycle)


@microsoft_patch_tuesday_router.get(
    "/priority/{priority_level}",
    response_model=PatchTuesdayResponse,
    description="Get vulnerabilities by priority level",
)
async def get_by_priority(
    priority_level: str,
    cycle: Optional[str] = Query(
        None,
        description="Cycle in YYYY-Mmm format. Defaults to current month.",
        regex=r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$",
    ),
    include_epss: bool = Query(True, description="Include EPSS scores"),
    include_kev: bool = Query(True, description="Include CISA KEV data"),
) -> PatchTuesdayResponse:
    """
    Get vulnerabilities filtered by priority level.

    **Valid priority levels:** P0, P1, P2, P3
    """
    logger.info(f"Fetching {priority_level} priority items for cycle: {cycle or 'current'}")

    priority_level = priority_level.upper()
    if priority_level not in ["P0", "P1", "P2", "P3"]:
        return PatchTuesdayResponse(
            success=False,
            message=f"Invalid priority level '{priority_level}'. Valid values: P0, P1, P2, P3",
            summary=None,
            items=[],
        )

    request = PatchTuesdayRequest(
        cycle=cycle,
        include_epss=include_epss,
        include_kev=include_kev,
    )

    response = await get_patch_tuesday(request)

    if not response.success:
        return response

    # Filter by priority
    filtered_items = [item for item in response.items if item.prioritization.priority == priority_level]

    # Update counts
    if response.summary:
        from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
            PatchTuesdaySummary,
        )
        from app.integrations.microsoft_patch_tuesday.schema.microsoft_patch_tuesday import (
            PriorityCounts,
        )

        family_counts = {}
        for item in filtered_items:
            family_counts[item.affected.family] = family_counts.get(item.affected.family, 0) + 1

        # Create new priority counts with only the selected priority
        new_prio_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        new_prio_counts[priority_level] = len(filtered_items)

        summary = PatchTuesdaySummary(
            cycle=response.summary.cycle,
            patch_tuesday_date=response.summary.patch_tuesday_date,
            generated_utc=response.summary.generated_utc,
            unique_cves=len(set([x.cve for x in filtered_items])),
            total_records=len(filtered_items),
            by_priority=PriorityCounts(**new_prio_counts),
            by_family=dict(sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            by_severity=response.summary.by_severity,
        )
    else:
        summary = None

    return PatchTuesdayResponse(
        success=True,
        message=f"Found {len(filtered_items)} {priority_level} priority items",
        summary=summary,
        items=filtered_items,
    )


@microsoft_patch_tuesday_router.get(
    "/kev",
    response_model=PatchTuesdayResponse,
    description="Get only CISA KEV (Known Exploited Vulnerabilities) items",
)
async def get_kev_items(
    cycle: Optional[str] = Query(
        None,
        description="Cycle in YYYY-Mmm format. Defaults to current month.",
        regex=r"^\d{4}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$",
    ),
) -> PatchTuesdayResponse:
    """
    Get only vulnerabilities that are in the CISA Known Exploited Vulnerabilities catalog.

    These are actively exploited vulnerabilities that should be prioritized for immediate remediation.
    """
    logger.info(f"Fetching KEV items for cycle: {cycle or 'current'}")

    request = PatchTuesdayRequest(
        cycle=cycle,
        include_epss=True,
        include_kev=True,
    )

    response = await get_patch_tuesday(request)

    if not response.success:
        return response

    # Filter to only KEV items
    kev_items = [item for item in response.items if item.kev.in_kev]

    return PatchTuesdayResponse(
        success=True,
        message=f"Found {len(kev_items)} known exploited vulnerabilities",
        summary=response.summary,
        items=kev_items,
    )
