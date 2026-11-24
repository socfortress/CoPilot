"""What an error code means, in words a SOC analyst can act on.

A scan or a connection test that fails carries a code: copilot-prowler's (its ``MESSAGES`` in
``prowler-runner/runner/errors.py``, copied here word for word; ``tests/test_cloud_assessment_runner_contract.py``
compares them), or CoPilot's own. Only codes are stored; the text is looked up when a response
is built, so it never carries anything a cloud API said.
"""

from typing import Optional

from fastapi import HTTPException

from app.cloud_assessment.services.runner_client import RunnerError

#: copilot-prowler's codes that end a scan or a connection test, with its texts.
RUNNER_MESSAGES = {
    "invalid_request": "The request is not valid.",
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

#: CoPilot's own codes.
COPILOT_MESSAGES = {
    "credential_unreadable": "The stored credential can't be decrypted: CLOUD_ASSESSMENT_ENCRYPTION_KEY has changed since it was saved. Re-enter the credential.",
    "credential_missing": "The account has no credential. Enter one.",
    "runner_not_configured": "Cloud scans need PROWLER_RUNNER_TOKEN (at least 32 characters, the same value for copilot-backend and copilot-prowler).",
    "runner_token_rejected": "copilot-prowler refused CoPilot's PROWLER_RUNNER_TOKEN: both containers need the same value.",
    "runner_unreachable": "CoPilot couldn't reach copilot-prowler.",
    "runner_refused": "copilot-prowler refused the scan.",
    "results_lost": "copilot-prowler no longer holds the scan: it restarted, or deleted the results before CoPilot read them. Run the scan again.",
    "ingest_failed": "CoPilot couldn't store the scan's results. Run the scan again.",
    "findings_unreadable": "CoPilot couldn't read any of copilot-prowler's findings: run the same CoPilot version for copilot-backend and copilot-prowler.",
    "dispatch_lost": "CoPilot lost track of the scan while handing it to copilot-prowler. Run the scan again.",
}

ERROR_MESSAGES = {**RUNNER_MESSAGES, **COPILOT_MESSAGES}


def error_message(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return ERROR_MESSAGES.get(code, "The scan failed.")


def runner_http_error(error: RunnerError) -> HTTPException:
    """A runner failure as a route's answer: 503 when it isn't set up, 502 otherwise. Never a 401 or
    403 (the frontend would end the analyst's session), never the runner's own body."""
    if error.reason in ("not_configured", "bad_url"):
        return HTTPException(status_code=503, detail=error.message)
    return HTTPException(status_code=502, detail=error.message)


def scan_code_for(error: RunnerError) -> str:
    """The code a scan is failed with when copilot-prowler refused or couldn't take it."""
    if error.reason in ("not_configured", "bad_url", "runner_not_configured"):
        return "runner_not_configured"
    if error.reason == "token_rejected":
        return "runner_token_rejected"
    if error.reason in ("unreachable", "timeout"):
        return "runner_unreachable"
    if error.reason == "refused" and error.code in RUNNER_MESSAGES:
        return error.code
    return "runner_refused"
