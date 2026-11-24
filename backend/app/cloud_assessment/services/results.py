"""What a completed scan found: its checks, its findings, and how it maps onto compliance frameworks (#1328).

Compliance isn't stored: it is worked out from the scan's check results, each of which carries the
framework requirements its check covers (``CIS-5.0: ["1.1", …]``). copilot-prowler's catalog
(``GET /v1/compliance/{provider}``, Prowler's own framework files) adds the requirements' names and
the ones no check of the scan touched. Without the catalog (the runner unreachable) the figures are
the scan's alone, and the answer says so.

A requirement fails when any of its checks has an unmuted failure, is ``manual`` when its checks
found only items to review by hand, passes when they found only passes, and is ``not_assessed``
when none of them produced a finding (not run, excluded, or nothing to check).
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud_assessment.models.cloud_assessment import CloudAssessmentCheckResult
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentFinding
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan
from app.cloud_assessment.schema.cloud_assessment import SEVERITIES
from app.cloud_assessment.schema.cloud_assessment import CheckResultOut
from app.cloud_assessment.schema.cloud_assessment import ComplianceFrameworkOut
from app.cloud_assessment.schema.cloud_assessment import FindingOut
from app.cloud_assessment.schema.cloud_assessment import RequirementCheckOut
from app.cloud_assessment.schema.cloud_assessment import RequirementOut
from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerError
from app.cloud_assessment.utils import as_utc
from app.cloud_assessment.utils import clean_text

MAX_PAGE_SIZE = 200
MAX_QUERY = 200


def _severity_rank(column):
    return case({level: rank for rank, level in enumerate(SEVERITIES)}, value=column, else_=len(SEVERITIES))


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def require_completed(scan: CloudAssessmentScan) -> None:
    if scan.status != "completed":
        raise HTTPException(status_code=409, detail="The scan hasn't completed")


def check_status(row: CloudAssessmentCheckResult) -> str:
    if row.fail_count:
        return "fail"
    if row.manual_count:
        return "manual"
    if row.pass_count:
        return "pass"
    if row.muted_count:
        return "muted"
    return "no_findings"


def check_out(row: CloudAssessmentCheckResult) -> CheckResultOut:
    return CheckResultOut(
        check_id=row.check_id,
        title=row.title,
        service=row.service,
        severity=row.severity,
        description=row.description,
        risk=row.risk,
        remediation=row.remediation,
        remediation_urls=list(row.remediation_urls or []),
        additional_urls=list(row.additional_urls or []),
        categories=list(row.categories or []),
        compliance=dict(row.compliance or {}),
        passed=row.pass_count or 0,
        failed=row.fail_count or 0,
        manual=row.manual_count or 0,
        muted=row.muted_count or 0,
        status=check_status(row),
    )


async def list_checks(
    session: AsyncSession,
    scan: CloudAssessmentScan,
    status: Optional[str] = None,
    severity: Optional[List[str]] = None,
    service: Optional[str] = None,
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[CheckResultOut], int, List[str]]:
    require_completed(scan)
    model = CloudAssessmentCheckResult
    conditions = [model.scan_id == scan.id]
    if status == "fail":
        conditions.append(model.fail_count > 0)
    elif status == "manual":
        conditions.extend([model.fail_count == 0, model.manual_count > 0])
    elif status == "pass":
        conditions.extend([model.fail_count == 0, model.manual_count == 0, model.pass_count > 0])
    if severity:
        conditions.append(model.severity.in_(severity))
    if service:
        conditions.append(model.service == service)
    if query:
        pattern = _like(query[:MAX_QUERY])
        conditions.append(or_(model.check_id.like(pattern, escape="\\"), model.title.like(pattern, escape="\\")))
    total = (await session.execute(select(func.count()).select_from(model).where(*conditions))).scalar() or 0
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    rows = (
        (
            await session.execute(
                select(model)
                .where(*conditions)
                .order_by(_severity_rank(model.severity), model.fail_count.desc(), model.check_id)
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size),
            )
        )
        .scalars()
        .all()
    )
    services = (
        (
            await session.execute(
                select(model.service).where(model.scan_id == scan.id, model.service != "").distinct().order_by(model.service),
            )
        )
        .scalars()
        .all()
    )
    return [check_out(row) for row in rows], total, list(services)


async def list_findings(
    session: AsyncSession,
    scan: CloudAssessmentScan,
    severity: Optional[List[str]] = None,
    status: Optional[str] = None,
    check_id: Optional[str] = None,
    service: Optional[str] = None,
    region: Optional[str] = None,
    muted: Optional[bool] = None,
    new_only: bool = False,
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[FindingOut], int]:
    require_completed(scan)
    if scan.findings_pruned_at is not None:
        raise HTTPException(status_code=410, detail="This scan's findings were removed by retention: its counts and checks remain")
    model = CloudAssessmentFinding
    conditions = [model.scan_id == scan.id]
    if severity:
        conditions.append(model.severity.in_(severity))
    if status:
        conditions.append(model.status == status)
    if check_id:
        conditions.append(model.check_id == check_id)
    if service:
        conditions.append(model.service == service)
    if region:
        conditions.append(model.region == region)
    if muted is not None:
        conditions.append(model.muted.is_(muted))
    if new_only:
        conditions.append(model.is_new.is_(True))
    if query:
        pattern = _like(query[:MAX_QUERY])
        conditions.append(
            or_(
                model.resource_uid.like(pattern, escape="\\"),
                model.resource_name.like(pattern, escape="\\"),
                model.check_id.like(pattern, escape="\\"),
                model.status_extended.like(pattern, escape="\\"),
            ),
        )
    total = (await session.execute(select(func.count()).select_from(model).where(*conditions))).scalar() or 0
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    rows = (
        (
            await session.execute(
                select(model)
                .where(*conditions)
                .order_by(_severity_rank(model.severity), model.check_id, model.id)
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size),
            )
        )
        .scalars()
        .all()
    )
    titles: Dict[str, str] = {}
    check_ids = {row.check_id for row in rows}
    if check_ids:
        titles = dict(
            (
                await session.execute(
                    select(CloudAssessmentCheckResult.check_id, CloudAssessmentCheckResult.title).where(
                        and_(CloudAssessmentCheckResult.scan_id == scan.id, CloudAssessmentCheckResult.check_id.in_(check_ids)),
                    ),
                )
            ).all(),
        )
    return [
        FindingOut(
            id=row.id,
            finding_uid=row.finding_uid,
            check_id=row.check_id,
            check_title=titles.get(row.check_id) or None,
            status=row.status,
            severity=row.severity,
            muted=bool(row.muted),
            status_extended=row.status_extended,
            service=row.service,
            region=row.region,
            cloud_account_uid=row.cloud_account_uid,
            cloud_account_name=row.cloud_account_name,
            resource_uid=row.resource_uid,
            resource_name=row.resource_name,
            resource_type=row.resource_type,
            resource_tags=list(row.resource_tags or []),
            detected_at=as_utc(row.detected_at),
            first_seen_at=as_utc(row.first_seen_at),
            is_new=bool(row.is_new),
        )
        for row in rows
    ], total


# --- compliance ---------------------------------------------------------------------------------


async def _catalog(provider: Optional[str]) -> Optional[Dict[str, Dict[str, Any]]]:
    """The runner's frameworks for ``provider`` by key, or None when it can't be asked."""
    if not provider:
        return None
    try:
        async with RunnerClient.from_env() as runner:
            data = await runner.compliance_catalog(provider)
    except RunnerError:
        return None
    frameworks: Dict[str, Dict[str, Any]] = {}
    for item in data.get("frameworks", []):
        if isinstance(item, dict) and isinstance(item.get("key"), str) and item["key"] not in frameworks:
            frameworks[item["key"]] = item
    return frameworks


def _requirements(framework: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for raw in (framework or {}).get("requirements") or []:
        if isinstance(raw, dict) and isinstance(raw.get("id"), str) and raw["id"] not in result:
            result[raw["id"]] = raw
    return result


def requirement_status(checks: List[Optional[CloudAssessmentCheckResult]]) -> str:
    ran = [check for check in checks if check is not None]
    if any(check.fail_count for check in ran):
        return "fail"
    if any(check.manual_count for check in ran):
        return "manual"
    if any(check.pass_count for check in ran):
        return "pass"
    return "not_assessed"


def build_framework(
    key: str,
    mapping: Dict[str, List[str]],
    checks: Dict[str, CloudAssessmentCheckResult],
    catalog: Optional[Dict[str, Any]],
) -> Tuple[ComplianceFrameworkOut, List[RequirementOut]]:
    """One framework's figures and requirements. ``mapping``: requirement id -> the scan's check ids."""
    catalog_requirements = _requirements(catalog)
    ids = list(catalog_requirements) + [requirement for requirement in mapping if requirement not in catalog_requirements]
    requirements: List[RequirementOut] = []
    tally = {"pass": 0, "fail": 0, "manual": 0, "not_assessed": 0}
    for requirement_id in ids:
        raw = catalog_requirements.get(requirement_id, {})
        check_ids = list(dict.fromkeys([*mapping.get(requirement_id, []), *[c for c in raw.get("checks") or [] if isinstance(c, str)]]))
        rows = [checks.get(check_id) for check_id in check_ids]
        status = requirement_status(rows)
        tally[status] += 1
        requirements.append(
            RequirementOut(
                id=clean_text(requirement_id, 128),
                name=clean_text(raw.get("name"), 256) or None,
                description=clean_text(raw.get("description"), 1000) or None,
                section=clean_text(raw.get("section"), 256) or None,
                status=status,
                checks=[
                    RequirementCheckOut(
                        check_id=check_id,
                        title=row.title if row else None,
                        severity=row.severity if row else None,
                        passed=row.pass_count if row else 0,
                        failed=row.fail_count if row else 0,
                        manual=row.manual_count if row else 0,
                        muted=row.muted_count if row else 0,
                        ran=row is not None,
                    )
                    for check_id, row in zip(check_ids, rows)
                ],
            ),
        )
    framework = ComplianceFrameworkOut(
        key=key,
        framework=clean_text((catalog or {}).get("framework"), 128) or None,
        version=clean_text((catalog or {}).get("version"), 64) or None,
        name=clean_text((catalog or {}).get("name"), 256) or None,
        description=clean_text((catalog or {}).get("description"), 2000) or None,
        requirements_total=len(ids),
        passed=tally["pass"],
        failed=tally["fail"],
        manual=tally["manual"],
        not_assessed=tally["not_assessed"],
    )
    return framework, requirements


async def _scan_mappings(
    session: AsyncSession,
    scan: CloudAssessmentScan,
) -> Tuple[Dict[str, CloudAssessmentCheckResult], Dict[str, Dict[str, List[str]]]]:
    """The scan's checks by id, and per framework key: requirement id -> check ids."""
    rows = (await session.execute(select(CloudAssessmentCheckResult).where(CloudAssessmentCheckResult.scan_id == scan.id))).scalars().all()
    checks = {row.check_id: row for row in rows}
    mappings: Dict[str, Dict[str, List[str]]] = {}
    for row in rows:
        for key, requirement_ids in (row.compliance or {}).items():
            framework = mappings.setdefault(key, {})
            for requirement_id in requirement_ids:
                framework.setdefault(requirement_id, []).append(row.check_id)
    return checks, mappings


async def compliance_overview(
    session: AsyncSession,
    scan: CloudAssessmentScan,
    provider: Optional[str],
) -> Tuple[List[ComplianceFrameworkOut], bool]:
    require_completed(scan)
    checks, mappings = await _scan_mappings(session, scan)
    await session.commit()
    catalog = await _catalog(provider)
    frameworks = [build_framework(key, mapping, checks, (catalog or {}).get(key))[0] for key, mapping in mappings.items()]
    frameworks.sort(key=lambda framework: (framework.name or framework.key).lower())
    return frameworks, catalog is not None


async def compliance_detail(
    session: AsyncSession,
    scan: CloudAssessmentScan,
    provider: Optional[str],
    key: str,
) -> Tuple[ComplianceFrameworkOut, List[RequirementOut], bool]:
    require_completed(scan)
    checks, mappings = await _scan_mappings(session, scan)
    await session.commit()
    if key not in mappings:
        raise HTTPException(status_code=404, detail="The scan has no checks for that framework")
    catalog = await _catalog(provider)
    framework, requirements = build_framework(key, mappings[key], checks, (catalog or {}).get(key))
    return framework, requirements, catalog is not None
