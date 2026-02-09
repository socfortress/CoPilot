from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.utils import AuthHandler

from app.db.db_session import get_db
from app.integrations.github_audit.schema.github_audit import GitHubAuditRequest
from app.integrations.github_audit.schema.github_audit import GitHubAuditResponse
from app.integrations.github_audit.schema.github_audit import (
    GitHubAuditSummaryResponse,
)
from app.integrations.github_audit.services.github_audit import run_github_audit
from app.integrations.github_audit.services.github_audit import run_github_audit_summary

github_audit_router = APIRouter()


async def get_github_token_from_db(session: AsyncSession) -> str:
    """
    Retrieve GitHub token from database connector settings.
    You'll need to adapt this to your connector storage mechanism.
    """
    # TODO: Implement retrieval from your connector storage
    # This is a placeholder - implement based on your connector pattern
    from app.utils import get_connector_attribute

    try:
        token = await get_connector_attribute(
            connector_id=1,  # Your GitHub connector ID
            column_name="connector_api_key",
            session=session,
        )
        if not token:
            raise HTTPException(status_code=400, detail="GitHub token not configured")
        return token
    except Exception as e:
        logger.error(f"Failed to retrieve GitHub token: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve GitHub credentials")


@github_audit_router.post(
    "/audit",
    response_model=GitHubAuditResponse,
    description="Run a full GitHub organization security audit",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def run_audit(
    request: GitHubAuditRequest,
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditResponse:
    """
    Run a comprehensive security audit on a GitHub organization.

    This endpoint performs the following checks:

    **Organization Level:**
    - Two-factor authentication requirement
    - Default repository permissions
    - Member repository/public repo creation policies
    - Verified domains
    - SAML SSO enforcement

    **Repository Level:**
    - Branch protection rules
    - Secret scanning configuration
    - Dependabot alerts
    - Code scanning/GHAS
    - Private vulnerability reporting

    **GitHub Actions:**
    - Allowed actions policy
    - Default workflow token permissions

    **Members:**
    - Admin role distribution
    """
    logger.info(f"Running GitHub audit for organization: {request.organization}")

    try:
        token = await get_github_token_from_db(session)
        return await run_github_audit(token, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub audit failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {e}")


@github_audit_router.post(
    "/audit/summary",
    response_model=GitHubAuditSummaryResponse,
    description="Run a GitHub audit and return summary only",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def run_audit_summary(
    request: GitHubAuditRequest,
    session: AsyncSession = Depends(get_db),
) -> GitHubAuditSummaryResponse:
    """
    Run a GitHub security audit and return only the summary.

    This is a lighter endpoint suitable for dashboards that returns
    the overall score, grade, and top 10 findings.
    """
    logger.info(f"Running GitHub audit summary for organization: {request.organization}")

    try:
        token = await get_github_token_from_db(session)
        return await run_github_audit_summary(token, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub audit summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {e}")


@github_audit_router.get(
    "/checks",
    description="Get list of all available audit checks",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_checks():
    """Get list of all audit checks that will be performed"""
    return {
        "success": True,
        "message": "Available audit checks retrieved successfully",
        "checks": [
            {
                "id": "org-2fa-required",
                "name": "Two-Factor Authentication Required",
                "category": "organization",
                "severity": "critical",
            },
            {
                "id": "org-default-permission",
                "name": "Default Repository Permission",
                "category": "organization",
                "severity": "medium",
            },
            {
                "id": "org-public-repo-creation",
                "name": "Public Repository Creation",
                "category": "organization",
                "severity": "high",
            },
            {
                "id": "repo-branch-protection",
                "name": "Default Branch Protection",
                "category": "repository",
                "severity": "high",
            },
            {
                "id": "repo-secret-scanning",
                "name": "Secret Scanning",
                "category": "repository",
                "severity": "high",
            },
            {
                "id": "repo-dependabot-alerts",
                "name": "Dependabot Alerts",
                "category": "repository",
                "severity": "high",
            },
            {
                "id": "repo-code-scanning",
                "name": "Code Scanning (GHAS)",
                "category": "repository",
                "severity": "medium",
            },
            {
                "id": "actions-allowed-all",
                "name": "Actions Permission Policy",
                "category": "workflow",
                "severity": "medium",
            },
            {
                "id": "actions-default-token-perms",
                "name": "Default Workflow Token Permissions",
                "category": "workflow",
                "severity": "medium",
            },
        ],
    }
