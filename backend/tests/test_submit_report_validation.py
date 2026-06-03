"""Tests for SubmitReportRequest body-completeness validation.

A report submitted without its human-readable body fields must be rejected, not
silently persisted as a blank row. These are pure Pydantic-model tests — no DB
or app wiring required.

Run with: cd backend && pip install pytest && python -m pytest tests/
"""

import pytest
from pydantic import ValidationError

from app.ai_analyst.schema.ai_analyst import SubmitReportRequest

COMPLETE = dict(
    job_id="copilot-inv-1-abc",
    alert_id=1,
    customer_code="acme",
    severity_assessment="High",
    summary="Short tl;dr.",
    report_markdown="# Full report\n\nDetails.",
    recommended_actions="Isolate host.",
)


def test_complete_report_is_accepted():
    req = SubmitReportRequest(**COMPLETE)
    assert req.report_markdown == "# Full report\n\nDetails."


@pytest.mark.parametrize(
    "field", ["severity_assessment", "summary", "report_markdown", "recommended_actions"]
)
def test_missing_body_field_is_rejected(field):
    payload = {k: v for k, v in COMPLETE.items() if k != field}
    with pytest.raises(ValidationError) as excinfo:
        SubmitReportRequest(**payload)
    assert field in str(excinfo.value)


@pytest.mark.parametrize("field", ["summary", "report_markdown", "recommended_actions"])
def test_blank_or_whitespace_body_field_is_rejected(field):
    payload = {**COMPLETE, field: "   "}
    with pytest.raises(ValidationError) as excinfo:
        SubmitReportRequest(**payload)
    assert field in str(excinfo.value)


def test_control_chars_only_body_is_rejected():
    # strip_control_characters collapses this to "" before require_report_body runs.
    payload = {**COMPLETE, "report_markdown": "\x00\x01\x02"}
    with pytest.raises(ValidationError) as excinfo:
        SubmitReportRequest(**payload)
    assert "report_markdown" in str(excinfo.value)


def test_minimal_call_missing_all_bodies_is_rejected():
    # The exact failure mode from production: agent sends only the identifiers.
    with pytest.raises(ValidationError):
        SubmitReportRequest(job_id="j", alert_id=1, customer_code="acme")
