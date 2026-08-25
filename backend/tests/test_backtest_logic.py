"""Unit tests for the pure/local backtest computation (no Graylog/DB needed).

Covers timestamp parsing, window parsing, the sparkline, top-field derivation, and
the tumbling-window threshold simulation (count + distinct_count).
"""
from datetime import datetime
from datetime import timezone

from app.integrations.copilot_searches.services import backtest as bt


def _epoch(y, mo, d, h, mi, s=0):
    return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc).timestamp()


def test_parse_window_seconds():
    assert bt._parse_window_seconds("10m") == 600
    assert bt._parse_window_seconds("1h") == 3600
    assert bt._parse_window_seconds("30s") == 30
    assert bt._parse_window_seconds("1d") == 86400
    assert bt._parse_window_seconds("300") == 300
    assert bt._parse_window_seconds(120) == 120
    assert bt._parse_window_seconds("nonsense") is None
    assert bt._parse_window_seconds("") is None
    assert bt._parse_window_seconds(True) is None


def test_to_epoch_variants():
    ref = _epoch(2026, 8, 20, 12, 0, 0)
    assert abs(bt._to_epoch("2026-08-20T12:00:00.000Z") - ref) < 1
    assert abs(bt._to_epoch("2026-08-20 12:00:00") - ref) < 1
    assert abs(bt._to_epoch("2026-08-20T12:00:00+0000") - ref) < 1
    assert bt._to_epoch(None) is None
    assert bt._to_epoch("") is None


def test_sparkline_buckets_by_hour():
    base = _epoch(2026, 8, 20, 12, 0, 0)
    rows = [(base + i * 60, {}) for i in range(5)]  # 5 events in the same hour
    rows += [(base + 3700, {})]  # one event in the next hour
    spark = bt._sparkline(rows, 3600)
    assert len(spark) == 2
    assert spark[0]["count"] == 5
    assert spark[1]["count"] == 1


def test_top_fields_only_varied():
    samples = [
        {"source": "host-a", "user": "alice"},
        {"source": "host-a", "user": "bob"},
        {"source": "host-a", "user": "alice"},
    ]
    top = bt._top_fields(samples, ["source", "user"])
    assert "source" not in top  # single value -> not interesting
    assert top["user"][0] == {"value": "alice", "count": 2}


def test_simulate_count_threshold():
    # 40 deletes by alice in one 10m window, 5 by bob -> only alice crosses ">30".
    base = _epoch(2026, 8, 20, 12, 0, 0)
    rows = [(base + i, {"data_office365_UserId": "alice"}) for i in range(40)]
    rows += [(base + i, {"data_office365_UserId": "bob"}) for i in range(5)]
    agg = {
        "enabled": True,
        "function": "count",
        "field": None,
        "group_by": ["data_office365_UserId"],
        "window": "10m",
        "threshold": 30,
        "condition": ">",
    }
    sim = bt._simulate_aggregation(rows, agg, truncated=False)
    assert sim["estimated_alerts"] == 1
    assert sim["top_offenders"][0]["group"] == "data_office365_UserId=alice"
    assert sim["top_offenders"][0]["peak"] == 40
    # sensitivity: alice (40) still crosses at 15 but not at 60; bob (5) never does.
    at15 = next(s["alerts"] for s in sim["sensitivity"] if s["threshold"] == 15)
    at60 = next(s["alerts"] for s in sim["sensitivity"] if s["threshold"] == 60)
    assert at15 == 1
    assert at60 == 0


def test_simulate_distinct_count():
    # one user hitting 6 distinct hosts in a window; distinct_count > 5 -> fires.
    base = _epoch(2026, 8, 20, 12, 0, 0)
    rows = [(base + i, {"user": "eve", "host": f"h{i}"}) for i in range(6)]
    agg = {
        "enabled": True,
        "function": "distinct_count",
        "field": "host",
        "group_by": ["user"],
        "window": "10m",
        "threshold": 5,
        "condition": ">",
    }
    sim = bt._simulate_aggregation(rows, agg, truncated=False)
    assert sim["function"] == "distinct_count"
    assert sim["estimated_alerts"] == 1
    assert sim["top_offenders"][0]["peak"] == 6


def test_simulate_burst_straddling_boundary_still_fires():
    # 35 events by alice inside 9 minutes, deliberately straddling a 10-min epoch
    # boundary. Tumbling windows would split them (~e.g. 20+15) and miss ">30";
    # the sliding window must still fire exactly once.
    boundary = (_epoch(2026, 8, 20, 12, 0, 0) // 600) * 600  # a 10-min boundary
    start = boundary - 240  # start 4 min before the boundary → burst spans it
    rows = [(start + i * 15, {"u": "alice"}) for i in range(35)]  # 35 events over ~8.5 min
    agg = {
        "enabled": True, "function": "count", "group_by": ["u"],
        "window": "10m", "threshold": 30, "condition": ">",
    }
    sim = bt._simulate_aggregation(rows, agg, truncated=False)
    assert sim["estimated_alerts"] == 1
    assert sim["top_offenders"][0]["peak"] == 35


def test_simulate_sustained_flood_multiple_alerts():
    # 120 events over 20 min at one/10s = 60 per 10-min window (>30) -> 2 non-overlapping alerts.
    base = _epoch(2026, 8, 20, 12, 0, 0)
    rows = [(base + i * 10, {"u": "x"}) for i in range(120)]
    agg = {"enabled": True, "function": "count", "group_by": ["u"], "window": "10m", "threshold": 30, "condition": ">"}
    sim = bt._simulate_aggregation(rows, agg, truncated=False)
    assert sim["estimated_alerts"] >= 2  # sustained flood fires repeatedly, not once


def test_simulate_bad_window_returns_none():
    rows = [(_epoch(2026, 8, 20, 12, 0, 0), {"u": "x"})]
    agg = {"enabled": True, "function": "count", "group_by": ["u"], "window": "??", "threshold": 1, "condition": ">"}
    assert bt._simulate_aggregation(rows, agg, truncated=False) is None
