"""Test one set of cloud credentials with the Prowler SDK's own connection test.

Run by the runner with Prowler's interpreter (``python -I test_connection.py``), never
imported by the runner itself. Reads one JSON object on stdin and prints one line:

    PROWLER_RUNNER_RESULT {"ok": true|false, "error_class": "<exception class>"|null}

The credentials arrive on stdin only. Nothing about them, and none of Prowler's error
messages (they name accounts, roles and tenants), is printed: logging is switched
off and a failure is reported by its exception's class alone.
"""

import json
import logging
import sys

RESULT_PREFIX = "PROWLER_RUNNER_RESULT "


def _aws(auth):
    from prowler.providers.aws.aws_provider import AwsProvider

    arguments = {"raise_on_exception": False}
    for key in ("aws_access_key_id", "aws_secret_access_key", "aws_session_token"):
        if auth.get(key):
            arguments[key] = auth[key]
    if auth["method"] == "role":
        arguments.update(role_arn=auth["role_arn"], external_id=auth["external_id"], session_duration=auth["session_duration"])
    return AwsProvider.test_connection(**arguments)


def _azure(auth, scope):
    from prowler.providers.azure.azure_provider import AzureProvider

    subscriptions = scope.get("subscription_ids") or []
    return AzureProvider.test_connection(
        tenant_id=auth["tenant_id"],
        client_id=auth["client_id"],
        client_secret=auth["client_secret"],
        # Prowler then also checks the credentials can see this subscription.
        provider_id=subscriptions[0] if subscriptions else None,
        raise_on_exception=False,
    )


def _gcp(auth, scope):
    from prowler.providers.gcp.gcp_provider import GcpProvider

    key = auth["service_account_key"]
    projects = scope.get("project_ids") or []
    return GcpProvider.test_connection(
        service_account_key=key,
        # Prowler requires a project to check access to: the first one named, else the key's own.
        provider_id=projects[0] if projects else key["project_id"],
        raise_on_exception=False,
    )


def _m365(auth, scope):
    from prowler.providers.m365.m365_provider import M365Provider

    return M365Provider.test_connection(
        tenant_id=auth["tenant_id"],
        client_id=auth["client_id"],
        client_secret=auth["client_secret"],
        # Prowler checks the credentials belong to the tenant that has this domain.
        provider_id=scope["tenant_domain"],
        raise_on_exception=False,
    )


def run(payload):
    provider = payload["provider"]
    auth = payload["auth"]
    scope = payload.get("scope") or {}
    if provider == "aws":
        return _aws(auth)
    if provider == "azure":
        return _azure(auth, scope)
    if provider == "gcp":
        return _gcp(auth, scope)
    if provider == "m365":
        return _m365(auth, scope)
    raise ValueError("unknown provider")


def main():
    logging.disable(logging.CRITICAL)
    try:
        connection = run(json.loads(sys.stdin.read()))
        error = getattr(connection, "error", None)
        result = {"ok": bool(getattr(connection, "is_connected", False)), "error_class": type(error).__name__ if error else None}
    except Exception as error:  # noqa: BLE001 - every failure is reported by its class only
        result = {"ok": False, "error_class": type(error).__name__}
    sys.stdout.write(RESULT_PREFIX + json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
