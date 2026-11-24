"""Constants and request builders shared by the tests."""

import time
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from runner.settings import Settings

TESTS = Path(__file__).resolve().parent
FIXTURES = TESTS / "fixtures"
FAKES = TESTS / "fakes"
TOKEN = "t" * 40
SECRET = "Az.ure~Secret_Value-0123456789"
KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def with_settings(settings: Settings, **changes) -> Settings:
    return replace(settings, **changes)


def wait_for(client: TestClient, job_id: str, statuses=("completed", "failed", "cancelled"), timeout: float = 30) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        response = client.get(f"/v1/scans/{job_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in statuses:
            return body
        if time.monotonic() > deadline:
            raise AssertionError(f"scan stayed {body['status']}")
        time.sleep(0.05)


def aws_role_scan(**options) -> dict:
    return {
        "provider": "aws",
        "auth": {
            "method": "role",
            "role_arn": "arn:aws:iam::123456789012:role/ProwlerScan",
            "external_id": "copilot-0123456789abcdef",
            "base_credentials": {"access_key_id": KEY_ID, "secret_access_key": AWS_SECRET},
        },
        "scope": {"regions": ["eu-west-1", "us-east-1"]},
        "options": options,
    }


def azure_scan(secret: str = SECRET, **options) -> dict:
    return {
        "provider": "azure",
        "auth": {
            "method": "client_secret",
            "tenant_id": "11111111-2222-3333-4444-555555555555",
            "client_id": "66666666-7777-8888-9999-000000000000",
            "client_secret": secret,
        },
        "scope": {"subscription_ids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]},
        "options": options,
    }


def m365_scan(secret: str = SECRET, tenant_domain: str | None = "contoso.onmicrosoft.com") -> dict:
    scan = azure_scan(secret)
    scan["provider"] = "m365"
    scan["scope"] = {"tenant_domain": tenant_domain} if tenant_domain else {}
    return scan


PRIVATE_KEY = (
    "-----BEGIN PRIVATE KEY-----\n" + ("MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC" * 3) + "\n-----END PRIVATE KEY-----\n"
)


def gcp_key(**changes) -> dict:
    key = {
        "type": "service_account",
        "project_id": "acme-prod-123",
        "private_key_id": "0123456789abcdef0123456789abcdef01234567",
        "private_key": PRIVATE_KEY,
        "client_email": "prowler@acme-prod-123.iam.gserviceaccount.com",
        "client_id": "123456789012345678901",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/prowler%40acme-prod-123.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com",
    }
    key.update(changes)
    return key


def gcp_scan(**key_changes) -> dict:
    return {
        "provider": "gcp",
        "auth": {"method": "service_account_key", "service_account_key": gcp_key(**key_changes)},
        "scope": {"project_ids": ["acme-prod-123", "acme-dev-456"]},
    }
