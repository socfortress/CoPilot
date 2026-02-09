from datetime import datetime
from datetime import timezone
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.github_audit.model import GitHubAuditBaseline
from app.integrations.github_audit.model import GitHubAuditCheckExclusion
from app.integrations.github_audit.model import GitHubAuditConfig
from app.integrations.github_audit.model import GitHubAuditReport
from app.integrations.github_audit.schema.github_audit import AvailableChecksResponse
from app.integrations.github_audit.schema.github_audit import GitHubAuditBaselineCreate
from app.integrations.github_audit.schema.github_audit import (
    GitHubAuditBaselineResponse,
)
from app.integrations.github_audit.schema.github_audit import GitHubAuditConfigCreate
from app.integrations.github_audit.schema.github_audit import GitHubAuditConfigResponse
from app.integrations.github_audit.schema.github_audit import GitHubAuditConfigUpdate
from app.integrations.github_audit.schema.github_audit import GitHubAuditExclusionCreate
from app.integrations.github_audit.schema.github_audit import (
    GitHubAuditExclusionResponse,
)
from app.integrations.github_audit.schema.github_audit import GitHubAuditExclusionUpdate
from app.integrations.github_audit.schema.github_audit import (
    GitHubAuditReportListResponse,
)
from app.integrations.github_audit.schema.github_audit import GitHubAuditReportResponse
from app.integrations.github_audit.schema.github_audit import GitHubAuditRequest
from app.integrations.github_audit.schema.github_audit import GitHubAuditResponse
from app.integrations.github_audit.schema.github_audit import GitHubAuditSummaryResponse
from app.integrations.github_audit.services.github_audit import run_github_audit
from app.integrations.github_audit.services.github_audit import run_github_audit_summary

github_audit_router = APIRouter()


# ==================== Configuration Routes ====================


@github_audit_router.post(
    "/config",
    response_model=GitHubAuditConfigResponse,
    description="Create a new GitHub Audit configuration for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_config(
    config: GitHubAuditConfigCreate,
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditConfigResponse:
    """Create a new GitHub Audit configuration."""
    logger.info(f"Creating GitHub Audit config for customer: {config.customer_code}")

    # Check if config already exists for this customer + organization
    existing = await session.execute(
        select(GitHubAuditConfig).where(
            GitHubAuditConfig.customer_code == config.customer_code,
            GitHubAuditConfig.organization == config.organization,
        ),
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Configuration already exists for customer '{config.customer_code}' and organization '{config.organization}'",
        )

    db_config = GitHubAuditConfig(
        customer_code=config.customer_code,
        github_token=config.github_token,  # TODO: Encrypt before storing
        organization=config.organization,
        token_type=config.token_type,
        token_expires_at=config.token_expires_at,
        enabled=config.enabled,
        auto_audit_enabled=config.auto_audit_enabled,
        audit_schedule_cron=config.audit_schedule_cron,
        include_repos=config.include_repos,
        include_workflows=config.include_workflows,
        include_members=config.include_members,
        include_archived_repos=config.include_archived_repos,
        repo_filter_mode=config.repo_filter_mode,
        repo_filter_list=config.repo_filter_list,
        notify_on_critical=config.notify_on_critical,
        notify_on_high=config.notify_on_high,
        notification_webhook_url=config.notification_webhook_url,
        notification_email=config.notification_email,
        minimum_passing_score=config.minimum_passing_score,
        created_by=config.created_by,
    )

    session.add(db_config)
    await session.commit()
    await session.refresh(db_config)

    return GitHubAuditConfigResponse(
        success=True,
        message="GitHub Audit configuration created successfully",
        config=db_config,
    )


@github_audit_router.get(
    "/config",
    response_model=GitHubAuditConfigResponse,
    description="Get GitHub Audit configurations",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_configs(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditConfigResponse:
    """Get all GitHub Audit configurations, optionally filtered by customer."""
    query = select(GitHubAuditConfig)

    if customer_code:
        query = query.where(GitHubAuditConfig.customer_code == customer_code)

    result = await session.execute(query)
    configs = result.scalars().all()

    # Mask tokens in response
    for config in configs:
        if config.github_token:
            config.github_token = "***" + config.github_token[-4:] if len(config.github_token) > 4 else "***"

    return GitHubAuditConfigResponse(
        success=True,
        message=f"Found {len(configs)} configuration(s)",
        configs=list(configs),
    )


@github_audit_router.get(
    "/config/{config_id}",
    response_model=GitHubAuditConfigResponse,
    description="Get a specific GitHub Audit configuration",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_config(
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditConfigResponse:
    """Get a specific GitHub Audit configuration by ID."""
    result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Mask token
    if config.github_token:
        config.github_token = "***" + config.github_token[-4:] if len(config.github_token) > 4 else "***"

    return GitHubAuditConfigResponse(
        success=True,
        message="Configuration retrieved successfully",
        config=config,
    )


@github_audit_router.put(
    "/config/{config_id}",
    response_model=GitHubAuditConfigResponse,
    description="Update a GitHub Audit configuration",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_config(
    config_update: GitHubAuditConfigUpdate,
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditConfigResponse:
    """Update an existing GitHub Audit configuration."""
    result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Update fields that were provided
    update_data = config_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(config, field, value)

    config.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(config)

    # Mask token
    if config.github_token:
        config.github_token = "***" + config.github_token[-4:] if len(config.github_token) > 4 else "***"

    return GitHubAuditConfigResponse(
        success=True,
        message="Configuration updated successfully",
        config=config,
    )


@github_audit_router.delete(
    "/config/{config_id}",
    description="Delete a GitHub Audit configuration",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_config(
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
):
    """Delete a GitHub Audit configuration and all associated data."""
    result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Delete associated records
    await session.execute(
        select(GitHubAuditReport).where(GitHubAuditReport.config_id == config_id),
    )
    await session.execute(
        select(GitHubAuditCheckExclusion).where(GitHubAuditCheckExclusion.config_id == config_id),
    )
    await session.execute(
        select(GitHubAuditBaseline).where(GitHubAuditBaseline.config_id == config_id),
    )

    await session.delete(config)
    await session.commit()

    return {"success": True, "message": "Configuration deleted successfully"}


# ==================== Audit Execution Routes ====================


@github_audit_router.post(
    "/config/{config_id}/audit",
    response_model=GitHubAuditResponse,
    description="Run a GitHub audit using a saved configuration",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def run_audit_from_config(
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditResponse:
    """Run a GitHub audit using a saved configuration."""
    logger.info(f"Running GitHub audit from config ID: {config_id}")

    # Get configuration
    result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if not config.enabled:
        raise HTTPException(status_code=400, detail="This configuration is disabled")

    # Get exclusions for this config
    exclusions_result = await session.execute(
        select(GitHubAuditCheckExclusion).where(
            GitHubAuditCheckExclusion.config_id == config_id,
            GitHubAuditCheckExclusion.enabled == True,
        ),
    )
    exclusions = exclusions_result.scalars().all()

    # Build request from config
    repo_filter = None
    if config.repo_filter_mode == "include" and config.repo_filter_list:
        repo_filter = config.repo_filter_list

    request = GitHubAuditRequest(
        organization=config.organization,
        include_repos=config.include_repos,
        include_workflows=config.include_workflows,
        include_members=config.include_members,
        repo_filter=repo_filter,
    )

    # Create report record
    report = GitHubAuditReport(
        config_id=config.id,
        customer_code=config.customer_code,
        report_name=f"Audit-{config.organization}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        organization=config.organization,
        status="running",
        triggered_by="manual",
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    try:
        # Run the audit
        start_time = datetime.now(timezone.utc)
        audit_response = await run_github_audit(config.github_token, request)
        end_time = datetime.now(timezone.utc)

        # Apply exclusions to findings
        if exclusions:
            exclusion_set = {(e.check_id, e.resource_name) for e in exclusions}
            audit_response.top_findings = [
                f
                for f in audit_response.top_findings
                if (f.check_id, f.resource_name) not in exclusion_set and (f.check_id, None) not in exclusion_set
            ]

        # Update report with results
        report.status = "completed" if audit_response.success else "failed"
        report.audit_completed_at = end_time
        report.audit_duration_seconds = (end_time - start_time).total_seconds()

        if audit_response.summary:
            report.total_repos_audited = audit_response.summary.total_repos_audited
            report.total_checks = audit_response.summary.total_checks
            report.passed_checks = audit_response.summary.passed_checks
            report.failed_checks = audit_response.summary.failed_checks
            report.warning_checks = audit_response.summary.warning_checks
            report.critical_findings = audit_response.summary.critical_findings
            report.high_findings = audit_response.summary.high_findings
            report.medium_findings = audit_response.summary.medium_findings
            report.low_findings = audit_response.summary.low_findings
            report.score = audit_response.summary.score
            report.grade = audit_response.summary.grade

        report.full_report = audit_response.dict()
        report.top_findings = [f.dict() for f in audit_response.top_findings[:20]]

        # Update config with last audit info
        config.last_audit_at = end_time
        if audit_response.summary:
            config.last_audit_score = audit_response.summary.score
            config.last_audit_grade = audit_response.summary.grade

        await session.commit()

        return audit_response

    except Exception as e:
        logger.error(f"Audit failed: {e}")
        report.status = "failed"
        report.error_message = str(e)
        report.audit_completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise HTTPException(status_code=500, detail=f"Audit failed: {e}")


@github_audit_router.post(
    "/audit",
    response_model=GitHubAuditResponse,
    description="Run a one-time GitHub audit (without saving config)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def run_audit_adhoc(
    request: GitHubAuditRequest,
    github_token: str = Query(..., description="GitHub Personal Access Token"),
) -> GitHubAuditResponse:
    """Run a one-time GitHub audit without saving configuration."""
    logger.info(f"Running ad-hoc GitHub audit for organization: {request.organization}")

    try:
        return await run_github_audit(github_token, request)
    except Exception as e:
        logger.error(f"GitHub audit failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {e}")


@github_audit_router.post(
    "/config/{config_id}/audit/summary",
    response_model=GitHubAuditSummaryResponse,
    description="Run a GitHub audit and return summary only",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def run_audit_summary_from_config(
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditSummaryResponse:
    """Run a GitHub audit using saved config and return only the summary."""
    logger.info(f"Running GitHub audit summary from config ID: {config_id}")

    result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if not config.enabled:
        raise HTTPException(status_code=400, detail="This configuration is disabled")

    request = GitHubAuditRequest(
        organization=config.organization,
        include_repos=config.include_repos,
        include_workflows=config.include_workflows,
        include_members=config.include_members,
    )

    try:
        return await run_github_audit_summary(config.github_token, request)
    except Exception as e:
        logger.error(f"GitHub audit summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {e}")


# ==================== Report Routes ====================


@github_audit_router.get(
    "/reports",
    response_model=GitHubAuditReportListResponse,
    description="Get list of GitHub audit reports",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_reports(
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    config_id: Optional[int] = Query(None, description="Filter by config ID"),
    organization: Optional[str] = Query(None, description="Filter by organization"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of reports"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditReportListResponse:
    """Get list of GitHub audit reports with optional filters."""
    from sqlalchemy import func

    # Select only the columns we need for the list view (exclude large JSON columns)
    query = select(
        GitHubAuditReport.id,
        GitHubAuditReport.config_id,
        GitHubAuditReport.customer_code,
        GitHubAuditReport.report_name,
        GitHubAuditReport.organization,
        GitHubAuditReport.audit_started_at,
        GitHubAuditReport.audit_completed_at,
        GitHubAuditReport.audit_duration_seconds,
        GitHubAuditReport.total_repos_audited,
        GitHubAuditReport.total_checks,
        GitHubAuditReport.passed_checks,
        GitHubAuditReport.failed_checks,
        GitHubAuditReport.warning_checks,
        GitHubAuditReport.critical_findings,
        GitHubAuditReport.high_findings,
        GitHubAuditReport.medium_findings,
        GitHubAuditReport.low_findings,
        GitHubAuditReport.score,
        GitHubAuditReport.grade,
        GitHubAuditReport.status,
        GitHubAuditReport.triggered_by,
        GitHubAuditReport.triggered_by_user,
    ).order_by(GitHubAuditReport.audit_started_at.desc())

    if customer_code:
        query = query.where(GitHubAuditReport.customer_code == customer_code)
    if config_id:
        query = query.where(GitHubAuditReport.config_id == config_id)
    if organization:
        query = query.where(GitHubAuditReport.organization == organization)
    if status:
        query = query.where(GitHubAuditReport.status == status)

    # Get total count using a separate count query
    count_query = select(func.count(GitHubAuditReport.id))
    if customer_code:
        count_query = count_query.where(GitHubAuditReport.customer_code == customer_code)
    if config_id:
        count_query = count_query.where(GitHubAuditReport.config_id == config_id)
    if organization:
        count_query = count_query.where(GitHubAuditReport.organization == organization)
    if status:
        count_query = count_query.where(GitHubAuditReport.status == status)

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    rows = result.all()

    # Convert rows to dictionaries
    report_summaries = []
    for row in rows:
        report_dict = {
            "id": row.id,
            "config_id": row.config_id,
            "customer_code": row.customer_code,
            "report_name": row.report_name,
            "organization": row.organization,
            "audit_started_at": row.audit_started_at,
            "audit_completed_at": row.audit_completed_at,
            "audit_duration_seconds": row.audit_duration_seconds,
            "total_repos_audited": row.total_repos_audited,
            "total_checks": row.total_checks,
            "passed_checks": row.passed_checks,
            "failed_checks": row.failed_checks,
            "warning_checks": row.warning_checks,
            "critical_findings": row.critical_findings,
            "high_findings": row.high_findings,
            "medium_findings": row.medium_findings,
            "low_findings": row.low_findings,
            "score": row.score,
            "grade": row.grade,
            "status": row.status,
            "triggered_by": row.triggered_by,
            "triggered_by_user": row.triggered_by_user,
        }
        report_summaries.append(report_dict)

    return GitHubAuditReportListResponse(
        success=True,
        message=f"Found {total} report(s)",
        reports=report_summaries,
        total_count=total,
    )


@github_audit_router.get(
    "/reports/{report_id}",
    response_model=GitHubAuditReportResponse,
    description="Get a specific GitHub audit report with full details",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_report(
    report_id: int = Path(..., description="Report ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditReportResponse:
    """Get a specific GitHub audit report with full details."""
    result = await session.execute(
        select(GitHubAuditReport).where(GitHubAuditReport.id == report_id),
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return GitHubAuditReportResponse(
        success=True,
        message="Report retrieved successfully",
        report=report,
    )


@github_audit_router.delete(
    "/reports/{report_id}",
    description="Delete a GitHub audit report",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_report(
    report_id: int = Path(..., description="Report ID"),
    session: AsyncSession = Depends(get_db),
):
    """Delete a specific GitHub audit report."""
    result = await session.execute(
        select(GitHubAuditReport).where(GitHubAuditReport.id == report_id),
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await session.delete(report)
    await session.commit()

    return {"success": True, "message": "Report deleted successfully"}


# ==================== Exclusion Routes ====================


@github_audit_router.post(
    "/config/{config_id}/exclusions",
    response_model=GitHubAuditExclusionResponse,
    description="Add an exclusion rule for a specific audit check",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_exclusion(
    exclusion: GitHubAuditExclusionCreate,
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditExclusionResponse:
    """Create an exclusion rule for a specific check."""
    # Verify config exists
    config_result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    db_exclusion = GitHubAuditCheckExclusion(
        config_id=config_id,
        customer_code=config.customer_code,
        check_id=exclusion.check_id,
        resource_name=exclusion.resource_name,
        resource_type=exclusion.resource_type,
        reason=exclusion.reason,
        approved_by=exclusion.approved_by,
        approved_at=datetime.now(timezone.utc) if exclusion.approved_by else None,
        expires_at=exclusion.expires_at,
        created_by=exclusion.created_by,
    )

    session.add(db_exclusion)
    await session.commit()
    await session.refresh(db_exclusion)

    return GitHubAuditExclusionResponse(
        success=True,
        message="Exclusion created successfully",
        exclusion=db_exclusion,
    )


@github_audit_router.get(
    "/config/{config_id}/exclusions",
    response_model=GitHubAuditExclusionResponse,
    description="Get all exclusion rules for a configuration",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_exclusions(
    config_id: int = Path(..., description="Configuration ID"),
    include_expired: bool = Query(False, description="Include expired exclusions"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditExclusionResponse:
    """Get all exclusion rules for a configuration."""
    query = select(GitHubAuditCheckExclusion).where(
        GitHubAuditCheckExclusion.config_id == config_id,
    )

    if not include_expired:
        query = query.where(
            (GitHubAuditCheckExclusion.expires_at.is_(None)) | (GitHubAuditCheckExclusion.expires_at > datetime.now(timezone.utc)),
        )

    result = await session.execute(query)
    exclusions = result.scalars().all()

    return GitHubAuditExclusionResponse(
        success=True,
        message=f"Found {len(exclusions)} exclusion(s)",
        exclusions=list(exclusions),
    )


@github_audit_router.put(
    "/exclusions/{exclusion_id}",
    response_model=GitHubAuditExclusionResponse,
    description="Update an exclusion rule",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_exclusion(
    exclusion_update: GitHubAuditExclusionUpdate,
    exclusion_id: int = Path(..., description="Exclusion ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditExclusionResponse:
    """Update an exclusion rule."""
    result = await session.execute(
        select(GitHubAuditCheckExclusion).where(GitHubAuditCheckExclusion.id == exclusion_id),
    )
    exclusion = result.scalar_one_or_none()

    if not exclusion:
        raise HTTPException(status_code=404, detail="Exclusion not found")

    update_data = exclusion_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(exclusion, field, value)

    await session.commit()
    await session.refresh(exclusion)

    return GitHubAuditExclusionResponse(
        success=True,
        message="Exclusion updated successfully",
        exclusion=exclusion,
    )


@github_audit_router.delete(
    "/exclusions/{exclusion_id}",
    description="Delete an exclusion rule",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_exclusion(
    exclusion_id: int = Path(..., description="Exclusion ID"),
    session: AsyncSession = Depends(get_db),
):
    """Delete an exclusion rule."""
    result = await session.execute(
        select(GitHubAuditCheckExclusion).where(GitHubAuditCheckExclusion.id == exclusion_id),
    )
    exclusion = result.scalar_one_or_none()

    if not exclusion:
        raise HTTPException(status_code=404, detail="Exclusion not found")

    await session.delete(exclusion)
    await session.commit()

    return {"success": True, "message": "Exclusion deleted successfully"}


# ==================== Baseline Routes ====================


@github_audit_router.post(
    "/config/{config_id}/baselines",
    response_model=GitHubAuditBaselineResponse,
    description="Create a baseline from a previous audit report",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_baseline(
    baseline: GitHubAuditBaselineCreate,
    config_id: int = Path(..., description="Configuration ID"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditBaselineResponse:
    """Create a baseline from a previous audit report."""
    # Verify config exists
    config_result = await session.execute(
        select(GitHubAuditConfig).where(GitHubAuditConfig.id == config_id),
    )
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # If baseline_report_id provided, extract expected checks from that report
    expected_checks = baseline.expected_checks
    if baseline.baseline_report_id:
        report_result = await session.execute(
            select(GitHubAuditReport).where(GitHubAuditReport.id == baseline.baseline_report_id),
        )
        report = report_result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Baseline report not found")

        if report.full_report:
            # Extract check statuses from report
            expected_checks = {}
            full_report = report.full_report

            # Organization checks
            if "organization_results" in full_report and full_report["organization_results"]:
                for check in full_report["organization_results"].get("checks", []):
                    expected_checks[check["check_id"]] = check["status"]

            # Repository checks
            for repo in full_report.get("repository_results", []):
                for check in repo.get("checks", []):
                    key = f"{check['check_id']}:{repo['repo_name']}"
                    expected_checks[key] = check["status"]

    # Deactivate other baselines for this config
    if baseline.is_active:
        await session.execute(
            select(GitHubAuditBaseline).where(GitHubAuditBaseline.config_id == config_id).where(GitHubAuditBaseline.is_active == True),
        )
        existing = await session.execute(
            select(GitHubAuditBaseline).where(
                GitHubAuditBaseline.config_id == config_id,
                GitHubAuditBaseline.is_active == True,
            ),
        )
        for b in existing.scalars().all():
            b.is_active = False

    db_baseline = GitHubAuditBaseline(
        config_id=config_id,
        customer_code=config.customer_code,
        name=baseline.name,
        description=baseline.description,
        expected_checks=expected_checks,
        baseline_report_id=baseline.baseline_report_id,
        is_active=baseline.is_active,
        created_by=baseline.created_by,
    )

    session.add(db_baseline)
    await session.commit()
    await session.refresh(db_baseline)

    return GitHubAuditBaselineResponse(
        success=True,
        message="Baseline created successfully",
        baseline=db_baseline,
    )


@github_audit_router.get(
    "/config/{config_id}/baselines",
    response_model=GitHubAuditBaselineResponse,
    description="Get all baselines for a configuration",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_baselines(
    config_id: int = Path(..., description="Configuration ID"),
    active_only: bool = Query(False, description="Only return active baseline"),
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditBaselineResponse:
    """Get all baselines for a configuration."""
    query = select(GitHubAuditBaseline).where(GitHubAuditBaseline.config_id == config_id)

    if active_only:
        query = query.where(GitHubAuditBaseline.is_active == True)

    result = await session.execute(query)
    baselines = result.scalars().all()

    return GitHubAuditBaselineResponse(
        success=True,
        message=f"Found {len(baselines)} baseline(s)",
        baselines=list(baselines),
    )


@github_audit_router.delete(
    "/baselines/{baseline_id}",
    description="Delete a baseline",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_baseline(
    baseline_id: int = Path(..., description="Baseline ID"),
    session: AsyncSession = Depends(get_db),
):
    """Delete a baseline."""
    result = await session.execute(
        select(GitHubAuditBaseline).where(GitHubAuditBaseline.id == baseline_id),
    )
    baseline = result.scalar_one_or_none()

    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    await session.delete(baseline)
    await session.commit()

    return {"success": True, "message": "Baseline deleted successfully"}


# ==================== Available Checks Route ====================


@github_audit_router.get(
    "/checks",
    response_model=AvailableChecksResponse,
    description="Get list of all available audit checks",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_checks() -> AvailableChecksResponse:
    """Get list of all audit checks that will be performed."""
    return AvailableChecksResponse(
        success=True,
        message="Available audit checks retrieved successfully",
        checks=[
            {
                "id": "org-2fa-required",
                "name": "Two-Factor Authentication Required",
                "category": "organization",
                "severity": "critical",
                "description": "Checks if 2FA is required for all organization members",
            },
            {
                "id": "org-default-permission",
                "name": "Default Repository Permission",
                "category": "organization",
                "severity": "medium",
                "description": "Checks the default permission level for new repositories",
            },
            {
                "id": "org-member-repo-creation",
                "name": "Member Repository Creation",
                "category": "organization",
                "severity": "low",
                "description": "Checks if members can create repositories",
            },
            {
                "id": "org-public-repo-creation",
                "name": "Public Repository Creation",
                "category": "organization",
                "severity": "high",
                "description": "Checks if members can create public repositories",
            },
            {
                "id": "org-verified-domains",
                "name": "Verified Domains",
                "category": "organization",
                "severity": "medium",
                "description": "Checks if organization has verified domains",
            },
            {
                "id": "org-sso-enforcement",
                "name": "SAML SSO Enforcement",
                "category": "organization",
                "severity": "high",
                "description": "Checks if SAML SSO is enforced",
            },
            {
                "id": "repo-branch-protection",
                "name": "Default Branch Protection",
                "category": "repository",
                "severity": "high",
                "description": "Checks if default branch has protection rules",
            },
            {
                "id": "repo-secret-scanning",
                "name": "Secret Scanning",
                "category": "repository",
                "severity": "high",
                "description": "Checks if secret scanning is enabled",
            },
            {
                "id": "repo-dependabot-alerts",
                "name": "Dependabot Alerts",
                "category": "repository",
                "severity": "high",
                "description": "Checks if Dependabot alerts are enabled",
            },
            {
                "id": "repo-code-scanning",
                "name": "Code Scanning (GHAS)",
                "category": "repository",
                "severity": "medium",
                "description": "Checks if code scanning is enabled",
            },
            {
                "id": "repo-private-vuln-reporting",
                "name": "Private Vulnerability Reporting",
                "category": "repository",
                "severity": "low",
                "description": "Checks if private vulnerability reporting is enabled",
            },
            {
                "id": "repo-license",
                "name": "Repository License",
                "category": "repository",
                "severity": "low",
                "description": "Checks if public repositories have a license",
            },
            {
                "id": "repo-branch-deletion",
                "name": "Default Branch Deletion Protection",
                "category": "repository",
                "severity": "high",
                "description": "Checks if default branch is protected from deletion",
            },
            {
                "id": "actions-allowed-all",
                "name": "Actions Permission Policy",
                "category": "workflow",
                "severity": "medium",
                "description": "Checks which GitHub Actions are allowed to run",
            },
            {
                "id": "actions-default-token-perms",
                "name": "Default Workflow Token Permissions",
                "category": "workflow",
                "severity": "medium",
                "description": "Checks default GITHUB_TOKEN permissions in workflows",
            },
        ],
    )
