"""Fixed error codes and texts.

A response never carries a request's values, a credential, or Prowler's own error
messages (they name accounts, roles and resources). Failures are reported as a code,
a fixed text and, at most, the name of the exception Prowler logged.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

MESSAGES = {
    "not_configured": "The runner has no PROWLER_RUNNER_TOKEN of at least 32 characters, so it accepts no requests.",
    "unauthorized": "Missing or wrong bearer token.",
    "invalid_request": "The request is not valid.",
    "busy": "The runner is already running as many scans as it may. Try again later.",
    "too_many_jobs": "The runner is holding too many finished scans. Delete some, then try again.",
    "not_found": "No such scan.",
    "not_ready": "The scan has not completed.",
    "no_artifact": "The scan has no such report.",
    "unknown_provider": "Unknown provider.",
    "tenant_domain_required": "Testing a Microsoft 365 connection needs one of the tenant's domains, for example contoso.onmicrosoft.com.",
    "auth_failed": "The cloud provider refused the credentials.",
    "permission_denied": "The credentials were accepted, but they lack a permission the scan needs.",
    "wrong_account": "The credentials don't belong to the account, subscription, project or tenant named.",
    "m365_powershell_failed": "Signed in to Microsoft Graph, but the Exchange or Teams connection failed. Check Exchange.ManageAsApp and the Global Reader role.",
    "connection_failed": "The cloud provider couldn't be reached, or answered with an error.",
    "timeout": "The scan ran past its time limit and was stopped.",
    "cancelled": "The scan was cancelled.",
    "scan_failed": "Prowler stopped with an error.",
    "output_invalid": "Prowler's output could not be read.",
    "internal": "The runner failed unexpectedly.",
}

# Prowler (and botocore) exception class names, by what they mean to the person running
# the scan. Checked in order: the first group with a matching name wins.
_CLASSIFICATION: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wrong_account", ("InvalidProviderId",)),
    ("m365_powershell_failed", ("ExchangeConnection", "TeamsConnection")),
    (
        "auth_failed",
        (
            "NoCredentials",
            "Credential",
            "ClientAuthentication",
            "AssumeRole",
            "SetUpSession",
            "SetUpIdentity",
            "GetTokenIdentity",
            "SessionTokenExpired",
            "NotValidClient",
            "NotValidTenant",
            "NotBelonging",
            "AccessKeyIDInvalid",
            "SecretAccessKeyInvalid",
            "LoadServiceAccountKey",
            "StaticCredentials",
        ),
    ),
    (
        "permission_denied",
        (
            "AccessDenied",
            "Unauthorized",
            "Forbidden",
            "NoSubscriptions",
            "NoAccesibleProjects",
            "NoAccessibleProjects",
            "GetOrganizationProjects",
        ),
    ),
    ("connection_failed", ("GraphConnection", "EndpointConnection", "ConnectTimeout", "ConnectionError", "HTTPResponse", "TestConnection")),
    (
        "invalid_request",
        (
            "ArgumentTypeValidation",
            "RoleArn",
            "IAMRoleARN",
            "InvalidPartition",
            "InvalidBoto3",
            "EnvironmentVariable",
            "NoAuthenticationMethod",
            "SetUpRegionConfig",
        ),
    ),
)


def classify(exception_names: Iterable[str], default: str = "scan_failed") -> str:
    """The error code for the exception class names Prowler reported."""
    names = [name for name in exception_names if name]
    for code, hints in _CLASSIFICATION:
        if any(hint in name for name in names for hint in hints):
            return code
    return default


# Codes that say something failed without saying what to fix.
_VAGUE = ("scan_failed", "connection_failed")


def classify_failure(critical: list[str], errors: list[str]) -> str:
    """The code for a scan Prowler stopped: from its CRITICAL exceptions, or, when those are
    vague, from its ERROR ones too. (A sign-in failure on Azure is logged as an ERROR
    ``ClientAuthenticationError`` followed by a CRITICAL ``AzureHTTPResponseError``.)"""
    code = classify(critical)
    if code in _VAGUE and errors:
        merged = classify(critical + errors)
        if merged not in _VAGUE:
            return merged
    return code


class RunnerError(Exception):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


def error_body(code: str) -> dict:
    return {"detail": MESSAGES[code], "code": code}


async def runner_error_handler(_request: Request, error: RunnerError) -> JSONResponse:
    return JSONResponse(error_body(error.code), status_code=error.status_code)


async def validation_error_handler(_request: Request, error: RequestValidationError) -> JSONResponse:
    # FastAPI's default answer echoes each invalid value back, secrets included. Name
    # the fields and the kind of problem only.
    fields = []
    for item in error.errors()[:50]:
        location = ".".join(str(part) for part in item.get("loc", ()) if not isinstance(part, int))
        fields.append({"field": location[:200], "problem": str(item.get("type", "invalid"))[:64]})
    return JSONResponse({**error_body("invalid_request"), "fields": fields}, status_code=422)


async def http_error_handler(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    if error.status_code == 404:
        return JSONResponse({"detail": "Not Found", "code": "not_found"}, status_code=404)
    if error.status_code == 405:
        return JSONResponse({"detail": "Method Not Allowed", "code": "invalid_request"}, status_code=405)
    return JSONResponse({"detail": "Request failed", "code": "invalid_request"}, status_code=error.status_code)
