"""Request validation: identifiers can't be read as options, secrets are bounded, nothing unknown passes."""

import pytest
from pydantic import ValidationError

from runner.models import ScanPayload
from tests.support import aws_role_scan
from tests.support import azure_scan
from tests.support import gcp_key
from tests.support import gcp_scan
from tests.support import m365_scan


def valid(payload):
    return ScanPayload.model_validate(payload).root


def invalid(payload):
    with pytest.raises(ValidationError):
        ScanPayload.model_validate(payload)


@pytest.mark.parametrize(
    "arn",
    [
        "arn:aws:iam::123456789012:role/ProwlerScan",
        "arn:aws-us-gov:iam::123456789012:role/path/to/ProwlerScan",
        "arn:aws-cn:iam::123456789012:role/prowler+scan@x=y,z.w-q",
    ],
)
def test_role_arns_accepted(arn):
    payload = aws_role_scan()
    payload["auth"]["role_arn"] = arn
    assert valid(payload).auth.role_arn == arn


@pytest.mark.parametrize(
    "arn",
    [
        "arn:aws:iam::12345:role/ProwlerScan",
        "arn:aws:iam::123456789012:user/someone",
        "--role=arn:aws:iam::123456789012:role/x",
        "arn:aws:iam::123456789012:role/ProwlerScan\n",
        "arn:aws:iam::123456789012:role/Prowler Scan",
    ],
)
def test_role_arns_refused(arn):
    payload = aws_role_scan()
    payload["auth"]["role_arn"] = arn
    invalid(payload)


@pytest.mark.parametrize("external_id", ["-I", "--external-id", "x", "a" * 1225, "abc def"])
def test_external_ids_refused(external_id):
    payload = aws_role_scan()
    payload["auth"]["external_id"] = external_id
    invalid(payload)


@pytest.mark.parametrize("region", ["us-east-1", "us-gov-west-1", "eusc-de-east-1", "ap-southeast-7", "us-isob-east-1"])
def test_regions_accepted(region):
    payload = aws_role_scan()
    payload["scope"]["regions"] = [region]
    assert valid(payload).scope.regions == [region]


@pytest.mark.parametrize("region", ["-f", "US-EAST-1", "us-east", "useast1", "us-east-1;id"])
def test_regions_refused(region):
    payload = aws_role_scan()
    payload["scope"]["regions"] = [region]
    invalid(payload)


@pytest.mark.parametrize("secret", ["", "has space", "line\nbreak", "tab\there", "x" * 1025, "nonascii-é"])
def test_client_secrets_refused(secret):
    invalid(azure_scan(secret))


def test_a_client_secret_never_shows_in_a_repr():
    request = valid(azure_scan())
    assert "Az.ure~Secret" not in repr(request)
    assert "Az.ure~Secret" not in str(request.model_dump())


@pytest.mark.parametrize("check", ["-x", "Check", "a b", "../../etc", ""])
def test_excluded_check_names_refused(check):
    invalid(azure_scan(excluded_checks=[check]))


def test_unknown_fields_and_providers_refused():
    payload = azure_scan()
    payload["auth"]["password"] = "x"
    invalid(payload)
    invalid({**azure_scan(), "extra": 1})
    invalid({**azure_scan(), "provider": "kubernetes"})


def test_m365_takes_a_domain_and_no_certificate():
    assert valid(m365_scan()).scope.tenant_domain == "contoso.onmicrosoft.com"
    invalid(m365_scan(tenant_domain="-x.example"))
    payload = m365_scan()
    payload["auth"] = {**payload["auth"], "method": "certificate"}
    invalid(payload)


@pytest.mark.parametrize(
    "change",
    [
        {"token_uri": "https://attacker.example/token"},
        {"universe_domain": "example.com"},
        {"type": "authorized_user"},
        {"private_key": "not a key " * 20},
        {"private_key_id": "XYZ"},
        {"client_x509_cert_url": "https://attacker.example/cert"},
    ],
)
def test_gcp_keys_refused(change):
    invalid(gcp_scan(**change))


def test_gcp_key_without_optional_fields():
    key = gcp_key()
    for name in ("auth_uri", "auth_provider_x509_cert_url", "client_x509_cert_url", "universe_domain"):
        key.pop(name)
    payload = gcp_scan()
    payload["auth"]["service_account_key"] = key
    rebuilt = valid(payload).auth.service_account_key.key_file()
    assert rebuilt["token_uri"] == "https://oauth2.googleapis.com/token"
    assert "client_x509_cert_url" not in rebuilt


def test_timeout_bounds():
    invalid(azure_scan(timeout_seconds=10))
    invalid(azure_scan(timeout_seconds=50000))
    assert valid(azure_scan(timeout_seconds=600)).options.timeout_seconds == 600
