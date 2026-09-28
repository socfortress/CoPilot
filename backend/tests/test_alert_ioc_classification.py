"""An IoC value CoPilot can't classify must not stop alert creation (#1183).

MISP composite attributes such as `ip-dst|port` reach the IoC field as
`0.0.0.0|4449`. `get_ioc_type()` matched no pattern and returned None,
`build_ioc_payload()` still returned a payload with `ioc_type=None`, and
`AlertIoCCreate` rejected it. That aborted the whole alert, the Graylog event was
never stamped with `COPILOT_ALERT_ID`, and it was selected again on every run —
enough of them filled every oldest-first batch and alert creation stopped.

Run with: cd backend && python -m pytest tests/test_alert_ioc_classification.py
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.incidents.schema.db_operations import AlertIoCCreate
from app.incidents.schema.db_operations import AlertIocValue
from app.incidents.services.incident_alert import build_ioc_payload
from app.incidents.services.incident_alert import classify_ioc_value
from app.incidents.services.incident_alert import get_ioc_type

SHA256 = "a" * 64
MD5 = "b" * 32


@pytest.mark.parametrize(
    "value, expected",
    [
        ("8.8.8.8", AlertIocValue.IP),
        ("2001:db8::1", AlertIocValue.IP),
        ("evil.example.com", AlertIocValue.DOMAIN),
        (SHA256, AlertIocValue.HASH),
        (MD5, AlertIocValue.HASH),
        ("https://evil.example.com/payload.exe", AlertIocValue.URL),
        ("  8.8.8.8  ", AlertIocValue.IP),
        ("0.0.0.0|4449", None),
        ("999.1.1.1", None),
        ("not an ioc", None),
    ],
)
def test_get_ioc_type(value, expected):
    assert get_ioc_type(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        # The values from the report (MISP ip-dst|port).
        ("0.0.0.0|4449", ("0.0.0.0", AlertIocValue.IP)),
        ("127.0.0.1|28027", ("127.0.0.1", AlertIocValue.IP)),
        # domain|ip keeps the IP; filename|hash keeps the hash, not the filename-as-domain.
        ("evil.example.com|1.2.3.4", ("1.2.3.4", AlertIocValue.IP)),
        (f"evil.exe|{SHA256}", (SHA256, AlertIocValue.HASH)),
        ("hostname.example.com|443", ("hostname.example.com", AlertIocValue.DOMAIN)),
        # Plain values pass through untouched.
        ("8.8.8.8", ("8.8.8.8", AlertIocValue.IP)),
        # Nothing classifiable anywhere.
        ("foo|bar", None),
        ("|", None),
        ("random text", None),
    ],
)
def test_classify_ioc_value(value, expected):
    assert classify_ioc_value(value) == expected


FIELD_NAMES = SimpleNamespace(ioc_field_names=["threat_intel_value"])


def test_composite_value_yields_valid_ioc():
    payload = asyncio.run(build_ioc_payload({"threat_intel_value": "0.0.0.0|4449"}, FIELD_NAMES))

    assert payload["ioc_value"] == "0.0.0.0"
    assert payload["ioc_type"] == AlertIocValue.IP
    assert "0.0.0.0|4449" in payload["ioc_description"]
    # The model that used to reject it now accepts it.
    AlertIoCCreate(
        alert_id=1,
        ioc_value=payload["ioc_value"],
        ioc_type=payload["ioc_type"],
        ioc_description=payload["ioc_description"],
    )


def test_unclassifiable_value_is_dropped_not_fatal():
    """No IoC is better than no alert: `None` means "create the alert without one"."""
    assert asyncio.run(build_ioc_payload({"threat_intel_value": "definitely not an ioc"}, FIELD_NAMES)) is None


def test_plain_value_keeps_default_description():
    payload = asyncio.run(build_ioc_payload({"threat_intel_value": "8.8.8.8"}, FIELD_NAMES))

    assert payload["ioc_value"] == "8.8.8.8"
    assert payload["ioc_description"] == "IOC Auto-Generated From SOCFortress CoPilot"


def test_missing_field_still_returns_none():
    assert asyncio.run(build_ioc_payload({"other": "x"}, FIELD_NAMES)) is None
