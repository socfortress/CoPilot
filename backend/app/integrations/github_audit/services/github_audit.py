import asyncio
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from loguru import logger

from app.integrations.github_audit.schema.github_audit import AuditCheck
from app.integrations.github_audit.schema.github_audit import AuditStatus
from app.integrations.github_audit.schema.github_audit import AuditSummary
from app.integrations.github_audit.schema.github_audit import GitHubAuditRequest
from app.integrations.github_audit.schema.github_audit import GitHubAuditResponse
from app.integrations.github_audit.schema.github_audit import (
    GitHubAuditSummaryResponse,
)
from app.integrations.github_audit.schema.github_audit import MemberAuditResult
from app.integrations.github_audit.schema.github_audit import OrganizationAuditResult
from app.integrations.github_audit.schema.github_audit import RepositoryAuditResult
from app.integrations.github_audit.schema.github_audit import SeverityLevel
from app.integrations.github_audit.schema.github_audit import WorkflowAuditResult

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"


class GitHubAuditService:
    """Service for performing GitHub organization security audits"""

    def __init__(self, token: str, organization: str):
        self.token = token
        self.organization = organization
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], int]:
        """Make a request to GitHub API"""
        url = f"{GITHUB_API_BASE}{endpoint}"

        try:
            response = await self.client.request(
                method,
                url,
                headers=self.headers,
                params=params,
            )
            if response.status_code == 200:
                return response.json(), response.status_code
            elif response.status_code == 404:
                return None, 404
            else:
                logger.warning(f"GitHub API error: {response.status_code} - {response.text[:200]}")
                return None, response.status_code
        except Exception as e:
            logger.error(f"GitHub API request failed: {e}")
            return None, 500

    async def _paginate(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Paginate through GitHub API results"""
        results = []
        params = params or {}
        params["per_page"] = 100
        page = 1

        while True:
            params["page"] = page
            data, status = await self._request("GET", endpoint, params)

            if status != 200 or not data:
                break

            if isinstance(data, list):
                results.extend(data)
                if len(data) < 100:
                    break
            else:
                results.append(data)
                break

            page += 1

        return results

    # ==================== Organization Checks ====================

    async def audit_organization(self) -> OrganizationAuditResult:
        """Audit organization-level security settings"""
        logger.info(f"Auditing organization: {self.organization}")

        checks: List[AuditCheck] = []

        # Get organization info
        org_data, status = await self._request("GET", f"/orgs/{self.organization}")

        if status != 200 or not org_data:
            return OrganizationAuditResult(
                org_name=self.organization,
                org_url=f"https://github.com/{self.organization}",
                checks=[
                    AuditCheck(
                        check_id="org-access",
                        check_name="Organization Access",
                        category="organization",
                        status=AuditStatus.FAIL,
                        severity=SeverityLevel.CRITICAL,
                        description="Unable to access organization",
                        recommendation="Verify the token has org:read permissions",
                    ),
                ],
                failed_count=1,
            )

        # Check: Two-factor authentication requirement
        checks.append(await self._check_2fa_requirement(org_data))

        # Check: Default repository permission
        checks.append(await self._check_default_repo_permission(org_data))

        # Check: Members can create repositories
        checks.append(await self._check_member_repo_creation(org_data))

        # Check: Members can create public repositories
        checks.append(await self._check_public_repo_creation(org_data))

        # Check: Verified domains
        checks.append(await self._check_verified_domains())

        # Check: SSO enforcement
        checks.append(await self._check_sso_enforcement())

        # Calculate counts
        passed = sum(1 for c in checks if c.status == AuditStatus.PASS)
        failed = sum(1 for c in checks if c.status == AuditStatus.FAIL)
        warnings = sum(1 for c in checks if c.status == AuditStatus.WARNING)

        return OrganizationAuditResult(
            org_name=self.organization,
            org_url=org_data.get("html_url", f"https://github.com/{self.organization}"),
            checks=checks,
            passed_count=passed,
            failed_count=failed,
            warning_count=warnings,
        )

    async def _check_2fa_requirement(self, org_data: Dict[str, Any]) -> AuditCheck:
        """Check if 2FA is required for organization members"""
        two_factor_required = org_data.get("two_factor_requirement_enabled", False)

        return AuditCheck(
            check_id="org-2fa-required",
            check_name="Two-Factor Authentication Required",
            category="organization",
            status=AuditStatus.PASS if two_factor_required else AuditStatus.FAIL,
            severity=SeverityLevel.CRITICAL,
            description="Checks if 2FA is required for all organization members",
            recommendation="Enable 2FA requirement in Organization Settings > Authentication security"
            if not two_factor_required
            else None,
            resource_name=self.organization,
            resource_type="organization",
        )

    async def _check_default_repo_permission(self, org_data: Dict[str, Any]) -> AuditCheck:
        """Check default repository permission level"""
        default_permission = org_data.get("default_repository_permission", "read")

        # Acceptable: none, read. Risky: write, admin
        is_secure = default_permission in ["none", "read"]

        return AuditCheck(
            check_id="org-default-permission",
            check_name="Default Repository Permission",
            category="organization",
            status=AuditStatus.PASS if is_secure else AuditStatus.WARNING,
            severity=SeverityLevel.MEDIUM,
            description=f"Default repository permission is set to '{default_permission}'",
            recommendation="Set default repository permission to 'read' or 'none' to follow least privilege"
            if not is_secure
            else None,
            details={"current_permission": default_permission},
            resource_name=self.organization,
            resource_type="organization",
        )

    async def _check_member_repo_creation(self, org_data: Dict[str, Any]) -> AuditCheck:
        """Check if members can create repositories"""
        can_create = org_data.get("members_can_create_repositories", True)

        return AuditCheck(
            check_id="org-member-repo-creation",
            check_name="Member Repository Creation",
            category="organization",
            status=AuditStatus.WARNING if can_create else AuditStatus.PASS,
            severity=SeverityLevel.LOW,
            description="Members can create repositories" if can_create else "Members cannot create repositories",
            recommendation="Consider restricting repository creation to admins for better governance"
            if can_create
            else None,
            resource_name=self.organization,
            resource_type="organization",
        )

    async def _check_public_repo_creation(self, org_data: Dict[str, Any]) -> AuditCheck:
        """Check if members can create public repositories"""
        can_create_public = org_data.get("members_can_create_public_repositories", True)

        return AuditCheck(
            check_id="org-public-repo-creation",
            check_name="Public Repository Creation",
            category="organization",
            status=AuditStatus.FAIL if can_create_public else AuditStatus.PASS,
            severity=SeverityLevel.HIGH,
            description="Members can create public repositories"
            if can_create_public
            else "Members cannot create public repositories",
            recommendation="Restrict public repository creation to prevent accidental exposure of internal code"
            if can_create_public
            else None,
            resource_name=self.organization,
            resource_type="organization",
        )

    async def _check_verified_domains(self) -> AuditCheck:
        """Check if organization has verified domains"""
        domains, status = await self._request("GET", f"/orgs/{self.organization}/domains")

        if status == 404:
            return AuditCheck(
                check_id="org-verified-domains",
                check_name="Verified Domains",
                category="organization",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="Domain verification not available (requires GitHub Enterprise)",
                resource_name=self.organization,
                resource_type="organization",
            )

        verified_domains = []
        if domains and isinstance(domains, list):
            verified_domains = [d for d in domains if d.get("is_verified", False)]

        has_verified = len(verified_domains) > 0

        return AuditCheck(
            check_id="org-verified-domains",
            check_name="Verified Domains",
            category="organization",
            status=AuditStatus.PASS if has_verified else AuditStatus.WARNING,
            severity=SeverityLevel.MEDIUM,
            description=f"Organization has {len(verified_domains)} verified domain(s)"
            if has_verified
            else "Organization has no verified domains",
            recommendation="Add and verify your organization's domain to improve trust and enable additional features"
            if not has_verified
            else None,
            details={"verified_domains": [d.get("domain") for d in verified_domains]} if verified_domains else None,
            resource_name=self.organization,
            resource_type="organization",
        )

    async def _check_sso_enforcement(self) -> AuditCheck:
        """Check if SAML SSO is enforced"""
        # This requires enterprise API access
        saml_data, status = await self._request("GET", f"/orgs/{self.organization}/saml")

        if status == 404:
            return AuditCheck(
                check_id="org-sso-enforcement",
                check_name="SAML SSO Enforcement",
                category="organization",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="SAML SSO configuration not available (requires GitHub Enterprise Cloud)",
                resource_name=self.organization,
                resource_type="organization",
            )

        enforced = saml_data.get("enforced", False) if saml_data else False

        return AuditCheck(
            check_id="org-sso-enforcement",
            check_name="SAML SSO Enforcement",
            category="organization",
            status=AuditStatus.PASS if enforced else AuditStatus.WARNING,
            severity=SeverityLevel.HIGH,
            description="SAML SSO is enforced" if enforced else "SAML SSO is not enforced",
            recommendation="Enable SAML SSO enforcement for centralized authentication" if not enforced else None,
            resource_name=self.organization,
            resource_type="organization",
        )

    # ==================== Repository Checks ====================

    async def audit_repositories(
        self,
        repo_filter: Optional[List[str]] = None,
    ) -> List[RepositoryAuditResult]:
        """Audit all repositories in the organization"""
        logger.info(f"Auditing repositories for organization: {self.organization}")

        # Get all repositories
        repos = await self._paginate(f"/orgs/{self.organization}/repos")

        if not repos:
            logger.warning("No repositories found or unable to fetch repositories")
            return []

        # Filter repos if specified
        if repo_filter:
            repos = [r for r in repos if r.get("name") in repo_filter]

        results = []

        # Audit repos concurrently in batches
        batch_size = 10
        for i in range(0, len(repos), batch_size):
            batch = repos[i : i + batch_size]
            batch_results = await asyncio.gather(*[self._audit_single_repo(repo) for repo in batch])
            results.extend(batch_results)

        return results

    async def _audit_single_repo(self, repo: Dict[str, Any]) -> RepositoryAuditResult:
        """Audit a single repository"""
        repo_name = repo.get("name", "unknown")
        full_name = repo.get("full_name", f"{self.organization}/{repo_name}")

        logger.debug(f"Auditing repository: {full_name}")

        checks: List[AuditCheck] = []

        # Skip archived repos
        if repo.get("archived", False):
            return RepositoryAuditResult(
                repo_name=repo_name,
                repo_full_name=full_name,
                repo_url=repo.get("html_url", ""),
                is_private=repo.get("private", True),
                is_archived=True,
                default_branch=repo.get("default_branch", "main"),
                checks=[
                    AuditCheck(
                        check_id="repo-archived",
                        check_name="Repository Archived",
                        category="repository",
                        status=AuditStatus.NOT_APPLICABLE,
                        severity=SeverityLevel.INFO,
                        description="Repository is archived - skipping security checks",
                        resource_name=repo_name,
                        resource_type="repository",
                    ),
                ],
            )

        # Check: Branch protection
        checks.append(await self._check_branch_protection(repo))

        # Check: Secret scanning
        checks.append(await self._check_secret_scanning(repo))

        # Check: Dependabot alerts
        checks.append(await self._check_dependabot_alerts(repo))

        # Check: Code scanning
        checks.append(await self._check_code_scanning(repo))

        # Check: Private vulnerability reporting
        checks.append(await self._check_private_vulnerability_reporting(repo))

        # Check: License
        checks.append(await self._check_license(repo))

        # Check: Default branch protection
        checks.append(await self._check_default_branch_deletion_protection(repo))

        # Calculate counts
        passed = sum(1 for c in checks if c.status == AuditStatus.PASS)
        failed = sum(1 for c in checks if c.status == AuditStatus.FAIL)
        warnings = sum(1 for c in checks if c.status == AuditStatus.WARNING)

        return RepositoryAuditResult(
            repo_name=repo_name,
            repo_full_name=full_name,
            repo_url=repo.get("html_url", ""),
            is_private=repo.get("private", True),
            is_archived=False,
            default_branch=repo.get("default_branch", "main"),
            checks=checks,
            passed_count=passed,
            failed_count=failed,
            warning_count=warnings,
        )

    async def _check_branch_protection(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if default branch has protection rules"""
        repo_name = repo.get("name")
        default_branch = repo.get("default_branch", "main")

        protection, status = await self._request(
            "GET",
            f"/repos/{self.organization}/{repo_name}/branches/{default_branch}/protection",
        )

        if status == 404:
            return AuditCheck(
                check_id="repo-branch-protection",
                check_name="Default Branch Protection",
                category="repository",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.HIGH,
                description=f"Default branch '{default_branch}' has no protection rules",
                recommendation="Enable branch protection rules to prevent direct pushes and require reviews",
                resource_name=repo_name,
                resource_type="repository",
            )

        # Check specific protection settings
        details = {}
        issues = []

        if protection:
            required_reviews = protection.get("required_pull_request_reviews")
            if not required_reviews:
                issues.append("Pull request reviews not required")
            else:
                details["required_approving_reviews"] = required_reviews.get("required_approving_review_count", 0)

            if not protection.get("enforce_admins", {}).get("enabled", False):
                issues.append("Admins can bypass protection")

            if not protection.get("required_status_checks"):
                issues.append("No required status checks")

            details["dismiss_stale_reviews"] = (required_reviews or {}).get("dismiss_stale_reviews", False)
            details["require_code_owner_reviews"] = (required_reviews or {}).get("require_code_owner_reviews", False)

        if issues:
            return AuditCheck(
                check_id="repo-branch-protection",
                check_name="Default Branch Protection",
                category="repository",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.MEDIUM,
                description=f"Branch protection enabled but with gaps: {', '.join(issues)}",
                recommendation="Strengthen branch protection by requiring reviews and enforcing for admins",
                details=details,
                resource_name=repo_name,
                resource_type="repository",
            )

        return AuditCheck(
            check_id="repo-branch-protection",
            check_name="Default Branch Protection",
            category="repository",
            status=AuditStatus.PASS,
            severity=SeverityLevel.HIGH,
            description=f"Default branch '{default_branch}' has protection rules enabled",
            details=details,
            resource_name=repo_name,
            resource_type="repository",
        )

    async def _check_secret_scanning(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if secret scanning is enabled"""
        repo_name = repo.get("name")

        security_config, status = await self._request(
            "GET",
            f"/repos/{self.organization}/{repo_name}",
        )

        if status != 200:
            return AuditCheck(
                check_id="repo-secret-scanning",
                check_name="Secret Scanning",
                category="repository",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="Unable to check secret scanning status",
                resource_name=repo_name,
                resource_type="repository",
            )

        security_and_analysis = security_config.get("security_and_analysis", {}) if security_config else {}
        secret_scanning = security_and_analysis.get("secret_scanning", {})
        secret_scanning_push = security_and_analysis.get("secret_scanning_push_protection", {})

        scanning_enabled = secret_scanning.get("status") == "enabled"
        push_protection_enabled = secret_scanning_push.get("status") == "enabled"

        if scanning_enabled and push_protection_enabled:
            return AuditCheck(
                check_id="repo-secret-scanning",
                check_name="Secret Scanning",
                category="repository",
                status=AuditStatus.PASS,
                severity=SeverityLevel.HIGH,
                description="Secret scanning and push protection are enabled",
                details={"secret_scanning": True, "push_protection": True},
                resource_name=repo_name,
                resource_type="repository",
            )
        elif scanning_enabled:
            return AuditCheck(
                check_id="repo-secret-scanning",
                check_name="Secret Scanning",
                category="repository",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.MEDIUM,
                description="Secret scanning enabled but push protection is disabled",
                recommendation="Enable secret scanning push protection to block secrets before they're committed",
                details={"secret_scanning": True, "push_protection": False},
                resource_name=repo_name,
                resource_type="repository",
            )
        else:
            return AuditCheck(
                check_id="repo-secret-scanning",
                check_name="Secret Scanning",
                category="repository",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.HIGH,
                description="Secret scanning is not enabled",
                recommendation="Enable secret scanning in repository Security settings",
                details={"secret_scanning": False, "push_protection": False},
                resource_name=repo_name,
                resource_type="repository",
            )

    async def _check_dependabot_alerts(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if Dependabot alerts are enabled"""
        repo_name = repo.get("name")

        # Check vulnerability alerts status
        vuln_alerts, status = await self._request(
            "GET",
            f"/repos/{self.organization}/{repo_name}/vulnerability-alerts",
        )

        if status == 204:  # 204 means enabled
            return AuditCheck(
                check_id="repo-dependabot-alerts",
                check_name="Dependabot Alerts",
                category="repository",
                status=AuditStatus.PASS,
                severity=SeverityLevel.HIGH,
                description="Dependabot vulnerability alerts are enabled",
                resource_name=repo_name,
                resource_type="repository",
            )
        elif status == 404:
            return AuditCheck(
                check_id="repo-dependabot-alerts",
                check_name="Dependabot Alerts",
                category="repository",
                status=AuditStatus.FAIL,
                severity=SeverityLevel.HIGH,
                description="Dependabot vulnerability alerts are not enabled",
                recommendation="Enable Dependabot alerts in repository Security settings",
                resource_name=repo_name,
                resource_type="repository",
            )
        else:
            return AuditCheck(
                check_id="repo-dependabot-alerts",
                check_name="Dependabot Alerts",
                category="repository",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="Unable to determine Dependabot alerts status",
                resource_name=repo_name,
                resource_type="repository",
            )

    async def _check_code_scanning(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if code scanning is enabled"""
        repo_name = repo.get("name")

        # Check for code scanning alerts
        alerts, status = await self._request(
            "GET",
            f"/repos/{self.organization}/{repo_name}/code-scanning/alerts",
            params={"per_page": 1},
        )

        if status == 200:
            return AuditCheck(
                check_id="repo-code-scanning",
                check_name="Code Scanning",
                category="repository",
                status=AuditStatus.PASS,
                severity=SeverityLevel.MEDIUM,
                description="Code scanning is enabled",
                resource_name=repo_name,
                resource_type="repository",
            )
        elif status == 404:
            return AuditCheck(
                check_id="repo-code-scanning",
                check_name="Code Scanning",
                category="repository",
                status=AuditStatus.WARNING,
                severity=SeverityLevel.MEDIUM,
                description="Code scanning is not configured",
                recommendation="Enable GitHub Advanced Security and configure CodeQL analysis",
                resource_name=repo_name,
                resource_type="repository",
            )
        else:
            return AuditCheck(
                check_id="repo-code-scanning",
                check_name="Code Scanning",
                category="repository",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="Unable to determine code scanning status",
                resource_name=repo_name,
                resource_type="repository",
            )

    async def _check_private_vulnerability_reporting(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if private vulnerability reporting is enabled"""
        repo_name = repo.get("name")

        # This is available in the repo data
        pvr_enabled = repo.get("private_vulnerability_reporting_enabled", False)

        return AuditCheck(
            check_id="repo-private-vuln-reporting",
            check_name="Private Vulnerability Reporting",
            category="repository",
            status=AuditStatus.PASS if pvr_enabled else AuditStatus.WARNING,
            severity=SeverityLevel.LOW,
            description="Private vulnerability reporting is enabled"
            if pvr_enabled
            else "Private vulnerability reporting is not enabled",
            recommendation="Enable private vulnerability reporting to allow security researchers to report issues confidentially"
            if not pvr_enabled
            else None,
            resource_name=repo_name,
            resource_type="repository",
        )

    async def _check_license(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if repository has a license"""
        repo_name = repo.get("name")
        license_info = repo.get("license")
        is_private = repo.get("private", True)

        if is_private:
            return AuditCheck(
                check_id="repo-license",
                check_name="Repository License",
                category="repository",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="License check not applicable for private repositories",
                resource_name=repo_name,
                resource_type="repository",
            )

        has_license = license_info is not None

        return AuditCheck(
            check_id="repo-license",
            check_name="Repository License",
            category="repository",
            status=AuditStatus.PASS if has_license else AuditStatus.WARNING,
            severity=SeverityLevel.LOW,
            description=f"Repository has license: {license_info.get('name', 'Unknown')}"
            if has_license
            else "Public repository has no license",
            recommendation="Add a LICENSE file to clarify usage terms for public repositories" if not has_license else None,
            details={"license": license_info.get("spdx_id") if license_info else None},
            resource_name=repo_name,
            resource_type="repository",
        )

    async def _check_default_branch_deletion_protection(self, repo: Dict[str, Any]) -> AuditCheck:
        """Check if default branch deletion is protected"""
        repo_name = repo.get("name")
        default_branch = repo.get("default_branch", "main")

        branch_info, status = await self._request(
            "GET",
            f"/repos/{self.organization}/{repo_name}/branches/{default_branch}",
        )

        if status != 200 or not branch_info:
            return AuditCheck(
                check_id="repo-branch-deletion",
                check_name="Default Branch Deletion Protection",
                category="repository",
                status=AuditStatus.NOT_APPLICABLE,
                severity=SeverityLevel.INFO,
                description="Unable to check branch deletion protection",
                resource_name=repo_name,
                resource_type="repository",
            )

        protected = branch_info.get("protected", False)

        return AuditCheck(
            check_id="repo-branch-deletion",
            check_name="Default Branch Deletion Protection",
            category="repository",
            status=AuditStatus.PASS if protected else AuditStatus.FAIL,
            severity=SeverityLevel.HIGH,
            description=f"Default branch '{default_branch}' is protected from deletion"
            if protected
            else f"Default branch '{default_branch}' can be deleted",
            recommendation="Enable branch protection to prevent accidental deletion of default branch" if not protected else None,
            resource_name=repo_name,
            resource_type="repository",
        )

    # ==================== Workflow/Actions Checks ====================

    async def audit_workflows(self) -> List[WorkflowAuditResult]:
        """Audit GitHub Actions settings and workflows"""
        logger.info(f"Auditing GitHub Actions for organization: {self.organization}")

        results: List[WorkflowAuditResult] = []

        # Get org-level actions permissions
        actions_perms, status = await self._request("GET", f"/orgs/{self.organization}/actions/permissions")

        if status == 200 and actions_perms:
            checks = []

            # Check allowed actions
            allowed_actions = actions_perms.get("allowed_actions", "all")
            if allowed_actions == "all":
                checks.append(
                    AuditCheck(
                        check_id="actions-allowed-all",
                        check_name="Actions Permission Policy",
                        category="workflow",
                        status=AuditStatus.WARNING,
                        severity=SeverityLevel.MEDIUM,
                        description="All GitHub Actions are allowed to run",
                        recommendation="Restrict to verified creators or specific allowed actions",
                        resource_name=self.organization,
                        resource_type="organization",
                    ),
                )
            elif allowed_actions == "selected":
                checks.append(
                    AuditCheck(
                        check_id="actions-allowed-selected",
                        check_name="Actions Permission Policy",
                        category="workflow",
                        status=AuditStatus.PASS,
                        severity=SeverityLevel.MEDIUM,
                        description="Only selected GitHub Actions are allowed",
                        resource_name=self.organization,
                        resource_type="organization",
                    ),
                )

            # Check default workflow permissions
            default_perms, _ = await self._request("GET", f"/orgs/{self.organization}/actions/permissions/workflow")

            if default_perms:
                default_token_perms = default_perms.get("default_workflow_permissions", "write")
                if default_token_perms == "write":
                    checks.append(
                        AuditCheck(
                            check_id="actions-default-token-perms",
                            check_name="Default Workflow Token Permissions",
                            category="workflow",
                            status=AuditStatus.WARNING,
                            severity=SeverityLevel.MEDIUM,
                            description="Default workflow token has write permissions",
                            recommendation="Set default workflow permissions to 'read' and grant write access explicitly where needed",
                            resource_name=self.organization,
                            resource_type="organization",
                        ),
                    )
                else:
                    checks.append(
                        AuditCheck(
                            check_id="actions-default-token-perms",
                            check_name="Default Workflow Token Permissions",
                            category="workflow",
                            status=AuditStatus.PASS,
                            severity=SeverityLevel.MEDIUM,
                            description="Default workflow token has read-only permissions",
                            resource_name=self.organization,
                            resource_type="organization",
                        ),
                    )

            results.append(
                WorkflowAuditResult(
                    repo_name=self.organization,
                    workflow_name="Organization Actions Settings",
                    workflow_path="N/A",
                    checks=checks,
                ),
            )

        return results

    # ==================== Member Checks ====================

    async def audit_members(self) -> List[MemberAuditResult]:
        """Audit organization members"""
        logger.info(f"Auditing members for organization: {self.organization}")

        results: List[MemberAuditResult] = []

        # Get all members
        members = await self._paginate(f"/orgs/{self.organization}/members")

        # Get admins
        admins = await self._paginate(f"/orgs/{self.organization}/members", params={"role": "admin"})
        admin_logins = set(m.get("login") for m in admins)

        for member in members:
            login = member.get("login", "unknown")
            is_admin = login in admin_logins

            checks = []

            # Check: Admin count
            if is_admin:
                checks.append(
                    AuditCheck(
                        check_id="member-is-admin",
                        check_name="Admin Role",
                        category="member",
                        status=AuditStatus.WARNING,
                        severity=SeverityLevel.LOW,
                        description=f"User '{login}' has admin role",
                        recommendation="Regularly review admin access and remove if not needed",
                        resource_name=login,
                        resource_type="member",
                    ),
                )

            results.append(
                MemberAuditResult(
                    username=login,
                    role="admin" if is_admin else "member",
                    checks=checks,
                ),
            )

        return results

    # ==================== Main Audit Function ====================

    async def run_full_audit(self, request: GitHubAuditRequest) -> GitHubAuditResponse:
        """Run a complete security audit"""
        logger.info(f"Starting full security audit for organization: {self.organization}")

        try:
            org_results = await self.audit_organization()

            repo_results = []
            if request.include_repos:
                repo_results = await self.audit_repositories(request.repo_filter)

            workflow_results = []
            if request.include_workflows:
                workflow_results = await self.audit_workflows()

            member_results = []
            if request.include_members:
                member_results = await self.audit_members()

            # Calculate summary
            all_checks: List[AuditCheck] = []
            all_checks.extend(org_results.checks)
            for repo in repo_results:
                all_checks.extend(repo.checks)
            for wf in workflow_results:
                all_checks.extend(wf.checks)
            for member in member_results:
                all_checks.extend(member.checks)

            # Filter out NOT_APPLICABLE checks for scoring
            scorable_checks = [c for c in all_checks if c.status != AuditStatus.NOT_APPLICABLE]

            total_checks = len(scorable_checks)
            passed = sum(1 for c in scorable_checks if c.status == AuditStatus.PASS)
            failed = sum(1 for c in scorable_checks if c.status == AuditStatus.FAIL)
            warnings = sum(1 for c in scorable_checks if c.status == AuditStatus.WARNING)

            # Count findings by severity (FAIL status only for severity counts)
            critical = sum(
                1 for c in scorable_checks
                if c.status == AuditStatus.FAIL and c.severity == SeverityLevel.CRITICAL
            )
            high = sum(
                1 for c in scorable_checks
                if c.status == AuditStatus.FAIL and c.severity == SeverityLevel.HIGH
            )
            medium = sum(
                1 for c in scorable_checks
                if c.status in [AuditStatus.FAIL, AuditStatus.WARNING] and c.severity == SeverityLevel.MEDIUM
            )
            low = sum(
                1 for c in scorable_checks
                if c.status in [AuditStatus.FAIL, AuditStatus.WARNING] and c.severity == SeverityLevel.LOW
            )

            # Calculate score using weighted pass rate
            # Weight checks by severity: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1
            if total_checks > 0:
                total_weight = 0
                earned_weight = 0

                for check in scorable_checks:
                    weight = 1  # default
                    if check.severity == SeverityLevel.CRITICAL:
                        weight = 4
                    elif check.severity == SeverityLevel.HIGH:
                        weight = 3
                    elif check.severity == SeverityLevel.MEDIUM:
                        weight = 2
                    elif check.severity == SeverityLevel.LOW:
                        weight = 1

                    total_weight += weight
                    if check.status == AuditStatus.PASS:
                        earned_weight += weight
                    elif check.status == AuditStatus.WARNING:
                        # Warnings get partial credit
                        earned_weight += weight * 0.5

                score = (earned_weight / total_weight) * 100 if total_weight > 0 else 100.0
            else:
                score = 100.0  # No checks = perfect score

            # Round to 1 decimal place
            score = round(score, 1)

            # Determine grade
            if score >= 90:
                grade = "A"
            elif score >= 80:
                grade = "B"
            elif score >= 70:
                grade = "C"
            elif score >= 60:
                grade = "D"
            else:
                grade = "F"

            logger.info(
                f"Audit complete - Total: {total_checks}, Passed: {passed}, "
                f"Failed: {failed}, Warnings: {warnings}, Score: {score}, Grade: {grade}"
            )

            summary = AuditSummary(
                organization=self.organization,
                audit_timestamp=datetime.now(timezone.utc).isoformat(),
                total_repos_audited=len(repo_results),
                total_checks=total_checks,
                passed_checks=passed,
                failed_checks=failed,
                warning_checks=warnings,
                critical_findings=critical,
                high_findings=high,
                medium_findings=medium,
                low_findings=low,
                score=score,
                grade=grade,
            )

            # Get top findings (failed checks sorted by severity)
            severity_order = {
                SeverityLevel.CRITICAL: 0,
                SeverityLevel.HIGH: 1,
                SeverityLevel.MEDIUM: 2,
                SeverityLevel.LOW: 3,
                SeverityLevel.INFO: 4,
            }
            failed_checks = [c for c in all_checks if c.status in [AuditStatus.FAIL, AuditStatus.WARNING]]
            top_findings = sorted(failed_checks, key=lambda c: severity_order.get(c.severity, 5))[:20]

            return GitHubAuditResponse(
                success=True,
                message=f"Audit completed successfully. Score: {score} ({grade})",
                summary=summary,
                organization_results=org_results,
                repository_results=repo_results,
                workflow_results=workflow_results,
                member_results=member_results,
                top_findings=top_findings,
            )

        except Exception as e:
            logger.error(f"Audit failed: {e}")
            return GitHubAuditResponse(
                success=False,
                message=f"Audit failed: {e}",
                summary=None,
                organization_results=None,
                repository_results=[],
                workflow_results=[],
                member_results=[],
                top_findings=[],
            )


# Service function wrappers
async def run_github_audit(
    token: str,
    request: GitHubAuditRequest,
) -> GitHubAuditResponse:
    """Run a GitHub organization security audit"""
    async with GitHubAuditService(token, request.organization) as service:
        return await service.run_full_audit(request)


async def run_github_audit_summary(
    token: str,
    request: GitHubAuditRequest,
) -> GitHubAuditSummaryResponse:
    """Run a GitHub audit and return summary only"""
    response = await run_github_audit(token, request)

    return GitHubAuditSummaryResponse(
        success=response.success,
        message=response.message,
        summary=response.summary,
        top_findings=response.top_findings[:10],
    )
