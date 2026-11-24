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
    assert classify_failure(collector.critical_names, collector.error_names) == "auth_failed"


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
