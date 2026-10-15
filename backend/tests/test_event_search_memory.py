"""Event search's memory (#1258): the request shapes and the rules that need no database.

Saved queries, recent ones and picked columns are kept per user and customer on the
server, so a user finds them on any device. The service and its routes run against a
real MySQL in tests/e2e/event_search_e2e.py; this file pins what is decided before the
database: what a valid search is, how times travel, and when two searches are the same.

Run with: cd backend && python -m pytest tests/test_event_search_memory.py
"""

import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.siem.schema.event_search import EventSearchState  # noqa: E402
from app.siem.schema.event_search import RecentQueryOut  # noqa: E402
from app.siem.schema.event_search import SaveQueryRequest  # noqa: E402
from app.siem.schema.event_search import SaveTemplateRequest  # noqa: E402
from app.siem.schema.event_search import SetColumnsRequest  # noqa: E402
from app.siem.utils.event_search import same_search  # noqa: E402

RELATIVE = {
    "source_name": "Wazuh",
    "query": "rule_level:>=10",
    "time_mode": "relative",
    "time_amount": 24,
    "time_unit": "h",
    "page_size": 50,
}
FROM = datetime(2026, 10, 1, 8, 0, tzinfo=timezone(timedelta(hours=2)))
TO = datetime(2026, 10, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
ABSOLUTE = {**RELATIVE, "time_mode": "absolute", "time_from": FROM, "time_to": TO}


class TestState:
    def test_a_relative_search_keeps_no_dates(self):
        state = EventSearchState(**RELATIVE, time_from=FROM, time_to=TO)
        assert state.time_from is None and state.time_to is None

    def test_an_absolute_search_travels_as_utc_with_its_offset(self):
        dumped = EventSearchState(**ABSOLUTE).model_dump(mode="json")
        assert dumped["time_from"] == "2026-10-01T06:00:00Z"
        assert dumped["time_to"] == "2026-10-01T08:00:00Z"

    def test_a_stored_naive_time_is_read_as_utc(self):
        row = RecentQueryOut(
            **{**ABSOLUTE, "time_from": datetime(2026, 10, 1, 6), "time_to": datetime(2026, 10, 1, 8)},
            ran_at=datetime(2026, 10, 2, 9),
        )
        dumped = row.model_dump(mode="json")
        assert (dumped["time_from"], dumped["ran_at"]) == ("2026-10-01T06:00:00Z", "2026-10-02T09:00:00Z")

    @pytest.mark.parametrize(
        "change",
        [
            {"time_from": None},
            {"time_to": None},
            {"time_from": TO, "time_to": FROM},
            {"time_to": FROM},
        ],
    )
    def test_an_absolute_search_needs_a_range_that_moves_forward(self, change):
        with pytest.raises(ValidationError):
            EventSearchState(**{**ABSOLUTE, **change})

    @pytest.mark.parametrize(
        "change",
        [
            {"source_name": "   "},
            {"time_mode": "sometime"},
            {"time_unit": "m"},
            {"time_amount": 0},
            {"page_size": 0},
            {"page_size": 1001},  # the events route's own ceiling
            {"query": "x" * 4001},
        ],
    )
    def test_what_is_not_a_search_is_refused(self, change):
        with pytest.raises(ValidationError):
            EventSearchState(**{**RELATIVE, **change})

    def test_text_is_trimmed(self):
        state = EventSearchState(**{**RELATIVE, "source_name": " Wazuh ", "query": "  a:b  "})
        assert (state.source_name, state.query) == ("Wazuh", "a:b")


class TestSave:
    def test_the_name_is_trimmed_and_required(self):
        assert SaveQueryRequest(**RELATIVE, name="  High level ").name == "High level"
        with pytest.raises(ValidationError):
            SaveQueryRequest(**RELATIVE, name="   ")
        with pytest.raises(ValidationError):
            SaveQueryRequest(**RELATIVE, name="x" * 81)


class TestColumns:
    def test_a_blank_header_falls_back_to_the_field(self):
        request = SetColumnsRequest(
            source_name="Wazuh",
            columns=[{"key": " agent_name ", "label": "  "}, {"key": "rule_level", "label": "Level"}],
        )
        assert [c.model_dump() for c in request.columns] == [
            {"key": "agent_name", "label": "agent_name"},
            {"key": "rule_level", "label": "Level"},
        ]

    def test_none_means_back_to_the_source_layout(self):
        assert SetColumnsRequest(source_name="Wazuh").columns is None
        assert SetColumnsRequest(source_name="Wazuh", columns=[]).columns == []

    @pytest.mark.parametrize("columns", [[{"key": "  ", "label": "x"}], [{"key": f"f{i}"} for i in range(51)]])
    def test_a_column_without_a_field_or_too_many_columns_are_refused(self, columns):
        with pytest.raises(ValidationError):
            SetColumnsRequest(source_name="Wazuh", columns=columns)


class TestTemplates:
    def test_a_template_has_a_name_and_at_least_one_column(self):
        template = SaveTemplateRequest(source_name="Wazuh", name="  Triage ", columns=[{"key": "agent_name", "label": ""}])
        assert template.name == "Triage"
        assert template.columns[0].model_dump() == {"key": "agent_name", "label": "agent_name"}

    @pytest.mark.parametrize(
        "change",
        [
            {"name": "  "},
            {"name": "x" * 81},
            {"columns": []},
            {"columns": [{"key": f"f{i}"} for i in range(51)]},
            {"source_name": ""},
        ],
    )
    def test_what_is_not_a_template_is_refused(self, change):
        with pytest.raises(ValidationError):
            SaveTemplateRequest(**{"source_name": "Wazuh", "name": "Triage", "columns": [{"key": "agent_name"}], **change})


class TestSameSearch:
    def test_the_page_size_does_not_make_another_search(self):
        assert same_search(EventSearchState(**RELATIVE), EventSearchState(**{**RELATIVE, "page_size": 250}))

    @pytest.mark.parametrize(
        "change",
        [{"source_name": "Office"}, {"query": "other"}, {"time_amount": 7}, {"time_unit": "d"}],
    )
    def test_anything_else_does(self, change):
        assert not same_search(EventSearchState(**RELATIVE), EventSearchState(**{**RELATIVE, **change}))

    def test_a_stored_absolute_range_matches_the_same_range_requested_with_an_offset(self):
        stored = RecentQueryOut(
            **{**ABSOLUTE, "time_from": datetime(2026, 10, 1, 6), "time_to": datetime(2026, 10, 1, 8)},
            ran_at=datetime(2026, 10, 2),
        )
        assert same_search(stored, EventSearchState(**ABSOLUTE))
        assert not same_search(stored, EventSearchState(**{**ABSOLUTE, "time_to": TO + timedelta(minutes=1)}))

    def test_relative_and_absolute_are_never_the_same(self):
        assert not same_search(EventSearchState(**RELATIVE), EventSearchState(**ABSOLUTE))
