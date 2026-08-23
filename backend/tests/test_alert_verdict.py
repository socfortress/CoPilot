"""Tests for the alert triage verdict — false positive classification (issue #1085).

Two pieces of real logic are covered here, both pure enough to test without a database:

1. `UpdateAlertVerdict` validation. A false-positive reason is mandatory when marking an
   alert a false positive and meaningless otherwise. Free-form classification via tags was
   the pre-existing workaround and the reason false-positive reporting was unreliable, so
   the request model has to refuse the shapes that would reintroduce it.
2. `build_alert_out`. Twenty call sites used to spell out the alert projection by hand;
   they now share this one helper, so a field silently missing from it would be missing
   from every listing endpoint at once.

Run with: cd backend && python -m pytest tests/test_alert_verdict.py
"""

import os
from datetime import datetime

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.incidents.models import Alert  # noqa: E402
from app.incidents.schema.db_operations import VERDICT_FILTER_UNTRIAGED  # noqa: E402
from app.incidents.schema.db_operations import AlertVerdict  # noqa: E402
from app.incidents.schema.db_operations import FalsePositiveReason  # noqa: E402
from app.incidents.schema.db_operations import UpdateAlertVerdict  # noqa: E402
from app.incidents.services.db_operations import build_alert_out  # noqa: E402


def _alert(**overrides) -> Alert:
    defaults = dict(
        id=1,
        alert_name="Suspicious PowerShell",
        alert_description="encoded command",
        status="OPEN",
        customer_code="ACME",
        source="wazuh",
        assigned_to="analyst1",
        escalated=False,
        alert_creation_time=datetime(2026, 8, 20, 12, 0, 0),
    )
    defaults.update(overrides)
    return Alert(**defaults)


# --- UpdateAlertVerdict validation -------------------------------------------------


def test_false_positive_requires_a_reason():
    """Without this, an analyst could mark FP with no category and the monthly
    "most common false positive categories" report would have a silent null bucket."""
    with pytest.raises(ValidationError):
        UpdateAlertVerdict(alert_id=1, verdict=AlertVerdict.FALSE_POSITIVE)


def test_false_positive_with_reason_is_accepted():
    payload = UpdateAlertVerdict(
        alert_id=1,
        verdict=AlertVerdict.FALSE_POSITIVE,
        verdict_reason=FalsePositiveReason.RULE_TOO_SENSITIVE,
        verdict_note="fires on every backup job",
    )
    assert payload.verdict is AlertVerdict.FALSE_POSITIVE
    assert payload.verdict_reason is FalsePositiveReason.RULE_TOO_SENSITIVE


def test_true_positive_rejects_a_false_positive_reason():
    """Silently dropping the mismatched reason would leave the caller believing it was
    recorded."""
    with pytest.raises(ValidationError):
        UpdateAlertVerdict(
            alert_id=1,
            verdict=AlertVerdict.TRUE_POSITIVE,
            verdict_reason=FalsePositiveReason.OTHER,
        )


def test_true_positive_needs_no_reason():
    payload = UpdateAlertVerdict(alert_id=1, verdict=AlertVerdict.TRUE_POSITIVE)
    assert payload.verdict_reason is None


def test_clearing_the_verdict_is_valid():
    """Omitting the verdict clears it back to untriaged — an analyst who mis-clicked needs
    a way back to "nobody has judged this", which is not the same as true positive."""
    payload = UpdateAlertVerdict(alert_id=1)
    assert payload.verdict is None
    assert payload.verdict_reason is None


def test_clearing_rejects_a_stray_reason():
    with pytest.raises(ValidationError):
        UpdateAlertVerdict(alert_id=1, verdict_reason=FalsePositiveReason.OTHER)


def test_note_is_length_capped_to_the_column():
    with pytest.raises(ValidationError):
        UpdateAlertVerdict(
            alert_id=1,
            verdict=AlertVerdict.FALSE_POSITIVE,
            verdict_reason=FalsePositiveReason.OTHER,
            verdict_note="x" * 1025,
        )


def test_untriaged_sentinel_is_not_a_storable_verdict():
    """UNTRIAGED is filter-only. If it ever became an AlertVerdict member, rows would start
    storing the string and the NULL-means-untriaged invariant would quietly split in two."""
    assert VERDICT_FILTER_UNTRIAGED not in {v.value for v in AlertVerdict}


# --- build_alert_out projection ----------------------------------------------------


def test_build_alert_out_projects_the_verdict_fields():
    alert = _alert(
        verdict=AlertVerdict.FALSE_POSITIVE.value,
        verdict_reason=FalsePositiveReason.KNOWN_APPLICATION.value,
        verdict_note="vendor agent",
        verdict_by="analyst1",
        verdict_at=datetime(2026, 8, 20, 13, 30, 0),
    )
    out = build_alert_out(alert)
    assert out.verdict == "FALSE_POSITIVE"
    assert out.verdict_reason == "KNOWN_APPLICATION"
    assert out.verdict_note == "vendor agent"
    assert out.verdict_by == "analyst1"
    # Serialized like the model's other datetimes, not as a raw datetime.
    assert out.verdict_at == "2026-08-20T13:30:00.000Z"


def test_build_alert_out_untriaged_alert_reports_nulls():
    out = build_alert_out(_alert())
    assert out.verdict is None
    assert out.verdict_reason is None
    assert out.verdict_at is None


def test_build_alert_out_defaults_omitted_relationships_to_empty():
    """Callers eager-load different subsets; omitting one must keep meaning "empty" exactly
    as it did when each site passed the lists positionally."""
    out = build_alert_out(_alert())
    assert out.comments == []
    assert out.assets == []
    assert out.tags == []
    assert out.iocs == []
    assert out.linked_cases == []


def test_build_alert_out_carries_the_pre_existing_scalars():
    """Guards the twenty-site extraction: every field the hand-written blocks passed must
    still arrive."""
    out = build_alert_out(_alert())
    assert out.id == 1
    assert out.alert_name == "Suspicious PowerShell"
    assert out.alert_description == "encoded command"
    assert out.status == "OPEN"
    assert out.customer_code == "ACME"
    assert out.source == "wazuh"
    assert out.assigned_to == "analyst1"
    assert out.escalated is False
    assert out.alert_creation_time == "2026-08-20T12:00:00.000Z"
