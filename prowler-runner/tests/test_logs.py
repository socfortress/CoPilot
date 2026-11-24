"""Prowler's log records, as Prowler 5.52.0 prints them with --only-logs."""

import pytest

from runner.errors import classify_failure
from runner.logs import LogCollector

# Captured from `prowler azure --sp-env-auth --only-logs` with an unknown tenant (ids replaced).
# Prowler's format isn't JSON-escaped: a message with a newline spans several lines.
AZURE_SIGN_IN_FAILURE = """\
{"timestamp": "2026-11-23 15:07:55,299", "filename": "azure_provider.py:940", "level": "ERROR", "module": "azure_provider", "message": "ClientAuthenticationError[933] -- DefaultAzureCredential failed to retrieve a token from the included credentials.
Attempted credentials:
\tEnvironmentCredential: Authentication failed: Unable to get authority configuration for https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000. Also please double check your tenant name or GUID is correct.
To mitigate this issue, please refer to the troubleshooting guidelines here at https://aka.ms/azsdk/python/identity/defaultazurecredential/troubleshoot."}
{"timestamp": "2026-11-23 15:07:55,301", "filename": "provider.py:719", "level": "CRITICAL", "module": "provider", "message": "AzureHTTPResponseError[404]: AzureHTTPResponseError[2010]: Error in HTTP response from Azure - DefaultAzureCredential failed to retrieve a token from the included credentials.
Attempted credentials:
\tEnvironmentCredential: Authentication failed: "quoted" text {"timestamp": "not a record"}
To mitigate this issue, please refer to the troubleshooting guidelines."}
"""

# The same records for a client secret that expired: Microsoft Entra ID's AADSTS7000222, on a
# continuation line as DefaultAzureCredential words it (made from the capture above, ids replaced).
AZURE_EXPIRED_SECRET = """\
{"timestamp": "2026-11-24 09:00:01,100", "filename": "azure_provider.py:940", "level": "ERROR", "module": "azure_provider", "message": "ClientAuthenticationError[933] -- DefaultAzureCredential failed to retrieve a token from the included credentials.
Attempted credentials:
\tEnvironmentCredential: Authentication failed: AADSTS7000222: The provided client secret keys for app '66666666-7777-8888-9999-000000000000' are expired. Visit the Azure portal to create new keys for your app: https://aka.ms/NewClientSecret, or consider using certificate credentials for added security: https://aka.ms/certCreds. Trace ID: 0000 Correlation ID: 0000 Timestamp: 2026-11-24 09:00:01Z
To mitigate this issue, please refer to the troubleshooting guidelines here at https://aka.ms/azsdk/python/identity/defaultazurecredential/troubleshoot."}
{"timestamp": "2026-11-24 09:00:01,102", "filename": "provider.py:719", "level": "CRITICAL", "module": "provider", "message": "AzureHTTPResponseError[404]: AzureHTTPResponseError[2010]: Error in HTTP response from Azure - DefaultAzureCredential failed to retrieve a token from the included credentials."}
"""

# Microsoft 365 through ClientSecretCredential: the code on the record's first line.
M365_EXPIRED_SECRET = """\
{"timestamp": "2026-11-24 09:00:02,000", "filename": "m365_provider.py:1089", "level": "ERROR", "module": "m365_provider", "message": "ClientAuthenticationError[1089] -- Authentication failed: AADSTS7000222: The provided client secret keys for app '66666666-7777-8888-9999-000000000000' are expired."}
{"timestamp": "2026-11-24 09:00:02,001", "filename": "provider.py:719", "level": "CRITICAL", "module": "provider", "message": "M365GetTokenIdentityError[6010]: Failed to get token identity"}
"""

AWS_NO_CREDENTIALS = """\
{"timestamp": "2026-11-23 14:47:12,266", "filename": "aws_provider.py:1471", "level": "CRITICAL", "module": "aws_provider", "message": "NoCredentialsError[1432]: Unable to locate credentials"}
{"timestamp": "2026-11-23 14:47:12,266", "filename": "provider.py:719", "level": "CRITICAL", "module": "provider", "message": "NoCredentialsError[383]: Unable to locate credentials"}
"""


def collect(text):
    collector = LogCollector()
    for line in text.splitlines():
        collector.feed(line)
    return collector


def test_a_message_spanning_lines_still_counts_once():
    collector = collect(AZURE_SIGN_IN_FAILURE)
    assert collector.error_lines == 1
    assert collector.critical_lines == 1
    assert collector.critical_names == ["AzureHTTPResponseError"]
    assert collector.error_names == ["ClientAuthenticationError"]
    assert collector.failure_names() == ["AzureHTTPResponseError", "ClientAuthenticationError"]


def test_an_azure_sign_in_failure_reads_as_refused_credentials():
    collector = collect(AZURE_SIGN_IN_FAILURE)
    assert classify_failure(collector.critical_names, collector.error_names) == "auth_failed"


def test_missing_aws_credentials():
    collector = collect(AWS_NO_CREDENTIALS)
    assert collector.failure_names() == ["NoCredentialsError"]
    assert classify_failure(collector.critical_names, collector.error_names) == "no_credentials"


@pytest.mark.parametrize("text", [AZURE_EXPIRED_SECRET, M365_EXPIRED_SECRET], ids=["azure", "m365"])
def test_an_expired_client_secret_says_so(text):
    collector = collect(text)
    assert collector.reasons == ["secret_expired"]
    assert classify_failure(collector.critical_names, collector.error_names, collector.reasons) == "secret_expired"
    kept = repr(collector.summary()) + repr(collector.failure_names()) + repr(collector.reasons)
    assert "AADSTS" not in kept and "66666666" not in kept


def test_a_refused_secret_is_still_refused_credentials():
    collector = collect(AZURE_SIGN_IN_FAILURE)
    assert collector.reasons == []
    assert classify_failure(collector.critical_names, collector.error_names, collector.reasons) == "auth_failed"


def test_a_mark_counts_only_in_an_error_or_a_critical():
    info = (
        '{"timestamp": "x", "filename": "f:1", "level": "INFO", "module": "m", "message": "AADSTS7000222 on the first line\n'
        "and AADSTS7000222 on the next"
    )
    assert collect(info).reasons == []
    # A continuation line of a CRITICAL record counts.
    lines = '{"timestamp": "x", "filename": "f:1", "level": "CRITICAL", "module": "m", "message": "Boom[1]: x\nAADSTS7000222 here'
    assert collect(lines).reasons == ["secret_expired"]


def test_the_command_line_being_refused_outranks_a_reason():
    assert classify_failure(["AzureArgumentTypeValidationError"], [], ["secret_expired"]) == "invalid_request"
    assert classify_failure(["Unexpected"], [], ["secret_expired"]) == "secret_expired"


def test_nothing_of_a_message_is_kept():
    collector = collect(AZURE_SIGN_IN_FAILURE)
    kept = repr(collector.summary()) + repr(collector.failure_names())
    assert "login.microsoftonline.com" not in kept
    assert "00000000-0000" not in kept


@pytest.mark.parametrize(
    "line",
    [
        "plain output",
        '{"timestamp": "x", "filename": "f:1", "level": "INFO", "module": "m", "message": "AWSAssumeRoleError[1]: info only"}',
        '{"level": "CRITICAL", "message": "AWSAssumeRoleError[1]: wrong key order"}',
        '  {"timestamp": "x", "filename": "f:1", "level": "CRITICAL", "module": "m", "message": "indented"}',
    ],
)
def test_lines_that_are_not_error_records_are_ignored(line):
    collector = collect(line)
    assert collector.critical_lines == 0
    assert collector.error_lines == 0


def test_a_vague_critical_keeps_its_code_without_errors():
    assert classify_failure(["AzureHTTPResponseError"], []) == "connection_failed"
    assert classify_failure(["Unexpected"], ["ClientError"]) == "scan_failed"
    assert classify_failure(["Unexpected"], ["AWSAssumeRoleError"]) == "auth_failed"
