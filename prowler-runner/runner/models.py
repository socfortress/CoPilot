"""Request bodies for scans and connection tests.

Every field is checked before anything reaches Prowler: identifiers by pattern (so no
value can be read as a command-line option), secrets by length and character set.
Secrets are ``SecretStr``, so a repr or a log line never shows them. Unknown fields
are refused, except in a GCP key file, whose extra keys are dropped.
"""

from __future__ import annotations

from typing import Annotated
from typing import Literal
from typing import Union

from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import RootModel
from pydantic import SecretStr

UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
ROLE_ARN_PATTERN = (
    r"^arn:aws(-cn|-us-gov|-iso|-iso-b|-iso-e|-iso-f|-eusc)?:iam::[0-9]{12}:role/([A-Za-z0-9_+=,.@-]+/)*[A-Za-z0-9_+=,.@-]{1,64}$"
)

Uuid = Annotated[str, Field(pattern=UUID_PATTERN)]
AwsRegion = Annotated[str, Field(pattern=r"^[a-z]{2,4}(-[a-z]+)+-[0-9]{1,2}$", max_length=32)]
CheckId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_]{0,127}$")]
ServiceName = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_]{0,63}$")]
GcpProjectId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
DomainName = Annotated[str, Field(pattern=r"^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$", max_length=253)]


def _secret(min_length: int, max_length: int, charset: str, multiline: bool = False):
    """A SecretStr of `min_length` to `max_length` characters, each in `charset`."""
    allowed = set(charset)

    def check(value: SecretStr) -> SecretStr:
        text = value.get_secret_value()
        if not min_length <= len(text) <= max_length:
            raise ValueError(f"must be {min_length} to {max_length} characters")
        if any(character not in allowed and not (multiline and character == "\n") for character in text):
            raise ValueError("contains a character that isn't allowed")
        return value

    return Annotated[SecretStr, AfterValidator(check)]


_PRINTABLE = "".join(chr(code) for code in range(0x21, 0x7F))
_BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_PEM = _BASE64 + "- "


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- AWS -------------------------------------------------------------------------


class AwsKeys(_Strict):
    access_key_id: str = Field(pattern=r"^(AKIA|ASIA)[A-Z0-9]{16}$")
    secret_access_key: _secret(16, 128, _BASE64)
    session_token: _secret(16, 8192, _BASE64) | None = None


class AwsRoleAuth(_Strict):
    """Assume the customer's read-only role, guarded by an External ID (recommended)."""

    method: Literal["role"]
    role_arn: str = Field(pattern=ROLE_ARN_PATTERN, max_length=2048)
    external_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_+=,.@:/-]{1,1223}$")
    # Prowler refreshes the role's credentials as they expire, so one hour suits any scan length.
    session_duration_seconds: int = Field(3600, ge=900, le=43200)
    # The identity that assumes the role. None: the host's own (EC2 instance role, ECS task role).
    base_credentials: AwsKeys | None = None


class AwsAccessKeysAuth(AwsKeys):
    method: Literal["access_keys"]


class AwsScope(_Strict):
    regions: list[AwsRegion] | None = Field(None, max_length=64)


# --- Azure and Microsoft 365 -------------------------------------------------------


class ClientSecretAuth(_Strict):
    """An app registration (service principal) and one of its client secrets."""

    method: Literal["client_secret"]
    tenant_id: Uuid
    client_id: Uuid
    client_secret: _secret(1, 1024, _PRINTABLE)


class AzureScope(_Strict):
    subscription_ids: list[Uuid] | None = Field(None, max_length=500)


class M365Scope(_Strict):
    # One of the tenant's domains. The connection test needs it (Prowler checks the
    # credentials belong to it); a scan doesn't.
    tenant_domain: DomainName | None = None


# --- GCP ---------------------------------------------------------------------------


def _pem_private_key(value: SecretStr) -> SecretStr:
    text = value.get_secret_value()
    if not text.lstrip().startswith("-----BEGIN PRIVATE KEY-----") or "-----END PRIVATE KEY-----" not in text:
        raise ValueError("is not a PEM private key")
    return value


class GcpServiceAccountKey(BaseModel):
    """A service-account key file. Its URLs are fixed: a key pointing its token URI
    elsewhere would send the signed assertion there."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["service_account"]
    project_id: GcpProjectId
    private_key_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    private_key: Annotated[_secret(100, 8192, _PEM, multiline=True), AfterValidator(_pem_private_key)]
    client_email: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}@[A-Za-z0-9.-]{1,253}$")
    client_id: str = Field(pattern=r"^[0-9]{1,32}$")
    auth_uri: Literal["https://accounts.google.com/o/oauth2/auth"] = "https://accounts.google.com/o/oauth2/auth"
    token_uri: Literal["https://oauth2.googleapis.com/token"] = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: Literal["https://www.googleapis.com/oauth2/v1/certs"] = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url: str | None = Field(None, pattern=r"^https://www\.googleapis\.com/robot/v1/metadata/x509/[A-Za-z0-9%._@-]{1,512}$")
    universe_domain: Literal["googleapis.com"] = "googleapis.com"

    def key_file(self) -> dict:
        """The key as Prowler and Google's libraries read it, rebuilt from the checked fields only."""
        key = self.model_dump(exclude_none=True)
        key["private_key"] = self.private_key.get_secret_value()
        return key


class GcpKeyAuth(_Strict):
    method: Literal["service_account_key"]
    service_account_key: GcpServiceAccountKey


class GcpScope(_Strict):
    project_ids: list[GcpProjectId] | None = Field(None, max_length=1000)
    excluded_project_ids: list[GcpProjectId] | None = Field(None, max_length=1000)
    organization_id: str | None = Field(None, pattern=r"^[0-9]{1,32}$")


# --- Scans -------------------------------------------------------------------------


class ScanOptions(_Strict):
    excluded_checks: list[CheckId] = Field(default_factory=list, max_length=2000)
    excluded_services: list[ServiceName] = Field(default_factory=list, max_length=500)
    # Seconds before the scan is stopped. None: the runner's PROWLER_SCAN_TIMEOUT.
    timeout_seconds: int | None = Field(None, ge=300, le=43200)


class AwsScanRequest(_Strict):
    provider: Literal["aws"]
    auth: Annotated[Union[AwsRoleAuth, AwsAccessKeysAuth], Field(discriminator="method")]
    scope: AwsScope = Field(default_factory=AwsScope)
    options: ScanOptions = Field(default_factory=ScanOptions)


class AzureScanRequest(_Strict):
    provider: Literal["azure"]
    auth: ClientSecretAuth
    scope: AzureScope = Field(default_factory=AzureScope)
    options: ScanOptions = Field(default_factory=ScanOptions)


class GcpScanRequest(_Strict):
    provider: Literal["gcp"]
    auth: GcpKeyAuth
    scope: GcpScope = Field(default_factory=GcpScope)
    options: ScanOptions = Field(default_factory=ScanOptions)


class M365ScanRequest(_Strict):
    provider: Literal["m365"]
    auth: ClientSecretAuth
    scope: M365Scope = Field(default_factory=M365Scope)
    options: ScanOptions = Field(default_factory=ScanOptions)


ScanRequest = Union[AwsScanRequest, AzureScanRequest, GcpScanRequest, M365ScanRequest]


class ScanPayload(RootModel):
    """The body of ``POST /v1/scans`` and ``POST /v1/connection-test``."""

    root: Annotated[ScanRequest, Field(discriminator="provider")]
