"""Request and response shapes for cloud accounts, scans and their results (#1328).

Identifiers are checked with the same patterns copilot-prowler applies (``prowler-runner/runner/models.py``;
``tests/test_cloud_assessment_runner_contract.py`` feeds what CoPilot builds to the runner's own models),
so a typo is refused when the account is saved, not when a scan starts. Credentials are ``SecretStr``
in, and never out: a response says whether one is stored and shows a hint, nothing more. Unknown
fields are refused.
"""

from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import SecretStr

PROVIDERS = ("aws", "azure", "gcp", "m365")
#: Which sign-in each provider takes. A pair outside this is refused.
AUTH_METHODS: Dict[str, tuple] = {
    "aws": ("role", "access_keys"),
    "azure": ("client_secret",),
    "m365": ("client_secret",),
    "gcp": ("service_account_key",),
}
SCHEDULES = ("off", "daily", "weekly")
SEVERITIES = ("critical", "high", "medium", "low", "informational", "unknown")
ACTIVE_STATUSES = ("queued", "starting", "running", "ingesting")
FINAL_STATUSES = ("completed", "failed", "cancelled")
SCAN_STATUSES = ACTIVE_STATUSES + FINAL_STATUSES
FINDING_STATUSES = ("FAIL", "MANUAL")
REPORT_KINDS = ("html", "csv")

UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
ROLE_ARN_PATTERN = (
    r"^arn:aws(-cn|-us-gov|-iso|-iso-b|-iso-e|-iso-f|-eusc)?:iam::[0-9]{12}:role/([A-Za-z0-9_+=,.@-]+/)*[A-Za-z0-9_+=,.@-]{1,64}$"
)
CHECK_ID_PATTERN = r"^[a-z0-9][a-z0-9_]{0,127}$"

Uuid = Annotated[str, Field(pattern=UUID_PATTERN)]
AwsRegion = Annotated[str, Field(pattern=r"^[a-z]{2,4}(-[a-z]+)+-[0-9]{1,2}$", max_length=32)]
CheckId = Annotated[str, Field(pattern=CHECK_ID_PATTERN)]
ServiceName = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_]{0,63}$")]
GcpProjectId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
DomainName = Annotated[str, Field(pattern=r"^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$", max_length=253)]

_PRINTABLE = frozenset(chr(code) for code in range(0x21, 0x7F))
_BASE64 = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
_PEM = _BASE64 | {"-", " ", "\n"}


def _secret(min_length: int, max_length: int, allowed: frozenset):
    """A SecretStr of ``min_length`` to ``max_length`` characters from ``allowed``. The message never
    shows the value."""

    def check(value: SecretStr) -> SecretStr:
        text = value.get_secret_value()
        if not min_length <= len(text) <= max_length:
            raise ValueError(f"must be {min_length} to {max_length} characters")
        if any(character not in allowed for character in text):
            raise ValueError("contains a character that isn't allowed")
        return value

    return Annotated[SecretStr, AfterValidator(check)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- what an admin sends -------------------------------------------------------------------


class AccountConfigIn(_Strict):
    """An account's settings, none of them secret. Which apply depends on the provider (the service
    refuses one that doesn't): ``role_arn`` an AWS role; ``regions`` AWS; ``tenant_id`` and
    ``client_id`` Azure and Microsoft 365; ``subscription_ids`` Azure; ``tenant_domain`` Microsoft 365
    (one of the tenant's domains, which the connection test needs); ``project_ids``,
    ``excluded_project_ids`` and ``organization_id`` GCP. The scan options apply to all."""

    role_arn: Optional[str] = Field(None, pattern=ROLE_ARN_PATTERN, max_length=2048)
    regions: Optional[List[AwsRegion]] = Field(None, max_length=64)
    tenant_id: Optional[Uuid] = None
    client_id: Optional[Uuid] = None
    subscription_ids: Optional[List[Uuid]] = Field(None, max_length=500)
    tenant_domain: Optional[DomainName] = None
    project_ids: Optional[List[GcpProjectId]] = Field(None, max_length=1000)
    excluded_project_ids: Optional[List[GcpProjectId]] = Field(None, max_length=1000)
    organization_id: Optional[str] = Field(None, pattern=r"^[0-9]{1,32}$")
    excluded_checks: List[CheckId] = Field(default_factory=list, max_length=2000)
    excluded_services: List[ServiceName] = Field(default_factory=list, max_length=500)
    # Seconds before copilot-prowler stops the scan. None: its PROWLER_SCAN_TIMEOUT.
    timeout_seconds: Optional[int] = Field(None, ge=300, le=43200)


def _pem_private_key(value: SecretStr) -> SecretStr:
    text = value.get_secret_value()
    if not text.lstrip().startswith("-----BEGIN PRIVATE KEY-----") or "-----END PRIVATE KEY-----" not in text:
        raise ValueError("is not a PEM private key")
    return value


class GcpServiceAccountKeyIn(BaseModel):
    """A GCP service-account key file, as downloaded. Its URLs are fixed (a key pointing its token URI
    elsewhere would send its signed assertion there), and only these fields are kept."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["service_account"]
    project_id: GcpProjectId
    private_key_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    private_key: Annotated[_secret(100, 8192, _PEM), AfterValidator(_pem_private_key)]
    client_email: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}@[A-Za-z0-9.-]{1,253}$")
    client_id: str = Field(pattern=r"^[0-9]{1,32}$")
    auth_uri: Literal["https://accounts.google.com/o/oauth2/auth"] = "https://accounts.google.com/o/oauth2/auth"
    token_uri: Literal["https://oauth2.googleapis.com/token"] = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: Literal["https://www.googleapis.com/oauth2/v1/certs"] = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url: Optional[str] = Field(
        None,
        pattern=r"^https://www\.googleapis\.com/robot/v1/metadata/x509/[A-Za-z0-9%._@-]{1,512}$",
    )
    universe_domain: Literal["googleapis.com"] = "googleapis.com"

    def key_file(self) -> Dict[str, Any]:
        """The key as Google's libraries read it, rebuilt from the checked fields only."""
        key = self.model_dump(exclude_none=True)
        key["private_key"] = self.private_key.get_secret_value()
        return key


class SecretIn(_Strict):
    """A credential. AWS: ``access_key_id`` and ``secret_access_key`` (for a role, the keys of the
    identity that assumes it). Azure and Microsoft 365: ``client_secret``. GCP: ``service_account_key``.
    Only long-lived AWS keys (``AKIA…``): a session's keys expire within hours."""

    access_key_id: Optional[str] = Field(None, pattern=r"^AKIA[A-Z0-9]{16}$")
    secret_access_key: Optional[_secret(16, 128, _BASE64)] = None
    client_secret: Optional[_secret(1, 1024, _PRINTABLE)] = None
    service_account_key: Optional[GcpServiceAccountKeyIn] = None


class _ScheduleFields(_Strict):
    schedule_hour: Optional[int] = Field(None, ge=0, le=23)
    schedule_weekday: Optional[int] = Field(None, ge=0, le=6)


class AccountCreate(_ScheduleFields):
    name: str = Field(min_length=1, max_length=100)
    provider: Literal["aws", "azure", "gcp", "m365"]
    auth_method: Literal["role", "access_keys", "client_secret", "service_account_key"]
    config: AccountConfigIn = Field(default_factory=AccountConfigIn)
    secret: Optional[SecretIn] = None
    # A client secret's expiry, as Azure showed it when it was made: the UI warns before it lapses.
    secret_expires_at: Optional[datetime] = None
    enabled: bool = True
    schedule: Literal["off", "daily", "weekly"] = "off"


class AccountUpdate(_ScheduleFields):
    """Only the fields sent change. ``config``, when sent, replaces every setting (the External ID
    stays). ``secret`` replaces the stored credential; ``remove_secret`` drops an AWS role's keys,
    so the role is assumed with the host's own identity. ``secret_expires_at: null`` clears it."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[AccountConfigIn] = None
    secret: Optional[SecretIn] = None
    remove_secret: bool = False
    secret_expires_at: Optional[datetime] = None
    enabled: Optional[bool] = None
    schedule: Optional[Literal["off", "daily", "weekly"]] = None


# --- what CoPilot answers ------------------------------------------------------------------


class ScanCounts(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    manual: int = 0
    muted: int = 0
    failed_critical: int = 0
    failed_high: int = 0
    failed_medium: int = 0
    failed_low: int = 0
    failed_informational: int = 0
    failed_unknown: int = 0
    new_failed: int = 0
    resolved_failed: int = 0


class ScanOut(BaseModel):
    id: int
    account_id: int
    account_name: Optional[str] = None
    provider: Optional[str] = None
    customer_code: str
    status: str
    trigger_type: str
    requested_by: Optional[str] = None
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    prowler_version: Optional[str] = None
    counts: ScanCounts
    # Checks that logged an error in a scan that still completed: a missing permission, usually.
    check_errors: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    prowler_errors: List[str] = Field(default_factory=list)
    reports: List[str] = Field(default_factory=list)
    findings_pruned: bool = False
    # The account's completed scan before this one, which ``new_failed`` and ``resolved_failed``
    # compare with. None: the account's first scan, so those two counts compare with nothing.
    previous_scan_id: Optional[int] = None


class AccountScanBrief(BaseModel):
    id: int
    status: str
    trigger_type: str
    queued_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    counts: Optional[ScanCounts] = None
    error_code: Optional[str] = None
    previous_scan_id: Optional[int] = None  # as ``ScanOut.previous_scan_id``


class AccountOut(BaseModel):
    id: int
    customer_code: str
    name: str
    provider: str
    auth_method: str
    config: Dict[str, Any]
    # AWS: the account in the role's ARN. Azure/Microsoft 365: the tenant. GCP: the key's project.
    cloud_account: Optional[str] = None
    # An AWS role's External ID: the value for the role's trust policy (Prowler's CloudFormation
    # template parameter ExternalId). Generated by CoPilot, never chosen or changed by a user.
    external_id: Optional[str] = None
    secret_configured: bool
    secret_hint: Optional[str] = None
    secret_expires_at: Optional[datetime] = None
    secret_expires_in_days: Optional[int] = None
    enabled: bool
    schedule: str
    schedule_hour: Optional[int] = None
    schedule_weekday: Optional[int] = None
    next_scheduled_at: Optional[datetime] = None
    last_connection_test_at: Optional[datetime] = None
    last_connection_ok: Optional[bool] = None
    last_connection_error: Optional[str] = None
    last_connection_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    last_scan: Optional[AccountScanBrief] = None
    last_completed_scan: Optional[AccountScanBrief] = None


class AccountResponse(BaseModel):
    success: bool
    message: str
    account: AccountOut


class AccountListResponse(BaseModel):
    success: bool
    message: str
    accounts: List[AccountOut]
    # Whether credentials can be saved and scans run at all, so the UI can say why not up front.
    encryption_key_configured: bool
    runner_configured: bool


class AccountDeleteResponse(BaseModel):
    success: bool
    message: str
    scans_deleted: int


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    ok: bool
    code: Optional[str] = None
    error_message: Optional[str] = None
    # The exception class Prowler raised, when the test failed: never its message.
    prowler_error: Optional[str] = None
    account: AccountOut


class ScanResponse(BaseModel):
    success: bool
    message: str
    scan: ScanOut


class ScanListResponse(BaseModel):
    success: bool
    message: str
    scans: List[ScanOut]
    total: int
    page: int
    page_size: int


class ScanDeleteResponse(BaseModel):
    success: bool
    message: str


class CheckResultOut(BaseModel):
    check_id: str
    title: str
    service: str
    severity: str
    description: Optional[str] = None
    risk: Optional[str] = None
    remediation: Optional[str] = None
    remediation_urls: List[str] = Field(default_factory=list)
    additional_urls: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    compliance: Dict[str, List[str]] = Field(default_factory=dict)
    passed: int = 0
    failed: int = 0
    manual: int = 0
    muted: int = 0
    status: str


class CheckListResponse(BaseModel):
    success: bool
    message: str
    checks: List[CheckResultOut]
    total: int
    page: int
    page_size: int
    services: List[str]


class FindingOut(BaseModel):
    id: int
    finding_uid: str
    check_id: str
    check_title: Optional[str] = None
    status: str
    severity: str
    muted: bool
    status_extended: Optional[str] = None
    service: str
    region: str
    cloud_account_uid: str
    cloud_account_name: str
    resource_uid: str
    resource_name: str
    resource_type: str
    resource_tags: List[str] = Field(default_factory=list)
    detected_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    is_new: bool


class FindingListResponse(BaseModel):
    success: bool
    message: str
    findings: List[FindingOut]
    total: int
    page: int
    page_size: int


class ComplianceFrameworkOut(BaseModel):
    key: str
    framework: Optional[str] = None
    version: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    # Requirements in Prowler's catalog for the framework; without the catalog, those the scan touched.
    requirements_total: int
    passed: int
    failed: int
    manual: int
    # In the catalog, but no check of theirs produced a finding in this scan.
    not_assessed: int


class ComplianceListResponse(BaseModel):
    success: bool
    message: str
    frameworks: List[ComplianceFrameworkOut]
    # False when copilot-prowler couldn't be asked for the catalog: the figures are then the scan's alone.
    catalog_available: bool


class RequirementCheckOut(BaseModel):
    check_id: str
    title: Optional[str] = None
    severity: Optional[str] = None
    passed: int = 0
    failed: int = 0
    manual: int = 0
    muted: int = 0
    ran: bool


class RequirementOut(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    section: Optional[str] = None
    # pass, fail, manual (only manual findings), not_assessed (no check of its produced a finding)
    status: str
    checks: List[RequirementCheckOut]


class ComplianceDetailResponse(BaseModel):
    success: bool
    message: str
    framework: ComplianceFrameworkOut
    requirements: List[RequirementOut]
    catalog_available: bool


class AvailabilityResponse(BaseModel):
    success: bool
    message: str
    encryption_key_configured: bool
    runner_configured: bool
    runner_reachable: bool
    runner_problem: Optional[str] = None
    runner_version: Optional[str] = None
    prowler_version: Optional[str] = None
    powershell: Optional[bool] = None
    providers: List[str] = Field(default_factory=list)
