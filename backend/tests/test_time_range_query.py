"""Time filters on `timestamp_utc` (connectors/wazuh_indexer/utils/universal.py).

`timestamp_utc` is epoch milliseconds (Wazuh pipeline) or ISO text (Office 365) and Graylog maps it as
a keyword, where a date range compares text: on the lab (2026-10-04) CoPilot's 24 h alert query
matched 0 of 3,701 Wazuh alerts. The window is applied to Graylog's `timestamp` (a date) instead;
sorting still uses the requested field.

Run with: cd backend && python -m pytest tests/test_time_range_query.py
"""

import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.wazuh_indexer.utils.universal import (  # noqa: E402
    AlertsQueryBuilder,
)
from app.connectors.wazuh_indexer.utils.universal import LogsQueryBuilder  # noqa: E402
from app.connectors.wazuh_indexer.utils.universal import time_range_query  # noqa: E402


def test_timestamp_utc_windows_use_timestamp():
    q = time_range_query("timestamp_utc", "2026-10-03T18:00:00", "now")
    assert q == {"range": {"timestamp": {"gte": "2026-10-03T18:00:00", "lte": "now", "format": "strict_date_optional_time"}}}


def test_other_fields_are_used_as_given():
    assert time_range_query("@timestamp", "a", "b") == {"range": {"@timestamp": {"gte": "a", "lte": "b"}}}


def test_the_builders_filter_on_timestamp_but_sort_on_the_requested_field():
    for builder in (AlertsQueryBuilder(), LogsQueryBuilder()):
        builder.add_time_range(timerange="24h", timestamp_field="timestamp_utc")
        builder.add_sort("timestamp_utc")
        query = builder.build()
        [window] = [c for c in query["query"]["bool"]["must"] if "range" in c]
        assert list(window["range"]) == ["timestamp"]
        assert query["sort"] == [{"timestamp_utc": {"order": "desc"}}]
    absolute = AlertsQueryBuilder().add_absolute_time_range("2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z", "timestamp_utc")
    assert list(absolute.query["query"]["bool"]["must"][-1]["range"]) == ["timestamp"]
