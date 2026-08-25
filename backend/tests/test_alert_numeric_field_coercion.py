"""Numeric values in string-typed alert fields must not stop ingest (#1096).

The lab stack produced `timestamp_utc` as epoch milliseconds — an `int` — and
`GenericSourceModel` declares it `Optional[str]`. Pydantic 1 stringified that
silently; Pydantic 2 raises `string_type`, `get_single_alert_details` turns any
exception into a 400, and the alert is never created.

The failure does not clear itself: `create_alert_auto_route` only stamps the
Graylog event with `copilot_alert_id` *after* a successful create, so an alert
that fails validation is selected again on the next scheduler run and fails
identically, forever. That is why the reported batch logged `0 created, 3 failed`
rather than a one-off error.

Run with: cd backend && python -m pytest tests/test_alert_numeric_field_coercion.py
"""

import pytest

from app.incidents.schema.incident_alert import GenericSourceModel

# The exact value from the report, and the field it arrived in.
EPOCH_MILLIS = 1787683237205


def _source(**overrides):
    """A minimal source document; `timestamp` is the only required field."""
    base = {"timestamp": "2026-08-25T18:45:47.240Z"}
    base.update(overrides)
    return base


def test_numeric_timestamp_utc_is_accepted():
    """The reported failure: epoch millis as an int."""
    model = GenericSourceModel(**_source(timestamp_utc=EPOCH_MILLIS))

    assert model.timestamp_utc == str(EPOCH_MILLIS)
    assert isinstance(model.timestamp_utc, str)


@pytest.mark.parametrize(
    "field, value",
    [
        ("timestamp", EPOCH_MILLIS),
        ("timestamp_utc", EPOCH_MILLIS),
        ("syslog_level", 3),
        ("process_id", 10388),
        ("agent_name", 12345),
        ("rule_description", 5716),
    ],
)
def test_every_string_field_accepts_a_number(field, value):
    """Not just the field that happened to break first.

    `syslog_level` is numeric on plenty of sources and `process_id` almost always
    is, so fixing `timestamp_utc` alone would leave the same crash waiting.
    """
    model = GenericSourceModel(**_source(**{field: value}))

    assert getattr(model, field) == str(value)


def test_float_values_are_accepted():
    """Some pipelines emit fractional epoch seconds."""
    model = GenericSourceModel(**_source(timestamp_utc=1787683237.205))

    assert model.timestamp_utc == "1787683237.205"


def test_string_values_are_untouched():
    """The common path must be byte-for-byte unchanged."""
    model = GenericSourceModel(
        **_source(
            timestamp_utc="2026-08-25T18:45:47.240Z",
            syslog_level="ALERT",
            process_id="10388",
        ),
    )

    assert model.timestamp_utc == "2026-08-25T18:45:47.240Z"
    assert model.syslog_level == "ALERT"
    assert model.process_id == "10388"


def test_booleans_are_not_stringified():
    """`bool` is an `int` subclass — coercing it would be a data change, not a
    format fix, so a bool must still fail validation rather than become "True"."""
    with pytest.raises(Exception) as exc:
        GenericSourceModel(**_source(timestamp_utc=True))

    assert "string_type" in str(exc.value)


def test_none_is_left_alone():
    """An explicit null stays null rather than becoming the string "None"."""
    model = GenericSourceModel(**_source(timestamp_utc=None))

    assert model.timestamp_utc is None


def test_extra_fields_are_not_coerced():
    """`extra="allow"` fields are undeclared, so their types are passed through
    as-is — the alert context keeps the original numeric values."""
    model = GenericSourceModel(**_source(data_win_system_processID=1234))

    assert model.data_win_system_processID == 1234


def test_source_document_is_not_mutated():
    """Coercion copies rather than editing the caller's document."""
    document = _source(timestamp_utc=EPOCH_MILLIS)

    GenericSourceModel(**document)

    assert document["timestamp_utc"] == EPOCH_MILLIS
