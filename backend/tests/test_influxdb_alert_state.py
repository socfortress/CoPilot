"""Healthcheck alert state is decided per monitored thing, from its latest status (#1118).

Three things made a recovered service keep reading Critical / Active:

* each row's status came from its own level, so a CRIT stayed "active" after an OK followed it;
* `exclude_ok` was pushed into the Flux query, so the recovery OK never reached the state logic;
* state was tracked per `_check_id`, but one check evaluates every host x unit -- which also let a
  sibling's OK hide a service that was still down.

And one thing the naive fix gets wrong: Telegraf tags systemd units with their state
(`active=failed` vs `active=active`), and `_level` is a tag, so a failure and its recovery are
*different Influx series*. Grouping by series key would never pair them. Verified against the dev
stack: stopping fluent-bit moved its rows from `active=active,sub=running` to
`active=inactive,sub=dead`.

The fake client below reproduces the Flux behaviour that matters -- `last()` per series, series
keyed on every tag including `_level` and the state tags, level filters applied only when they are
in the query text -- so these tests exercise the real failure modes, not a simplified model.

Run with: cd backend && python -m pytest tests/test_influxdb_alert_state.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from influxdb_client.client.flux_table import FluxRecord  # noqa: E402
from influxdb_client.client.flux_table import FluxTable  # noqa: E402

from app.connectors.influxdb.schema.alerts import AlertStatus  # noqa: E402
from app.connectors.influxdb.schema.alerts import (  # noqa: E402
    GetInfluxDBAlertQueryParams,
)
from app.connectors.influxdb.schema.alerts import InfluxDBAlert  # noqa: E402
from app.connectors.influxdb.schema.alerts import InfluxDBAlertResponse  # noqa: E402
from app.connectors.influxdb.schema.alerts import SeverityFilter  # noqa: E402
from app.connectors.influxdb.services import alerts as svc  # noqa: E402

SERVICES_CHECK = "111f856f0360d000"
HOST_OFFLINE_CHECK = "0c344c1192626000"


def service(hhmm, host, name, level, active="active", sub="running"):
    return _record(hhmm, SERVICES_CHECK, "CRITICAL SERVICES CHECK", level, host=host, name=name, active=active, sub=sub, load="loaded")


def host_offline(hhmm, host, level):
    return _record(hhmm, HOST_OFFLINE_CHECK, "Host Offline", level, host=host)


def _record(hhmm, check_id, check_name, level, **tags):
    hour, minute = map(int, hhmm.split(":"))
    values = {
        "_time": datetime(2026, 9, 17, hour, minute, tzinfo=timezone.utc),
        "_check_id": check_id,
        "_check_name": check_name,
        "_level": level,
        "_field": "_message",
        "_measurement": "statuses",
        "_value": f"{level}: {check_name} {tags}",
        **tags,
    }
    return FluxRecord(0, values=values)


def _series_key(record):
    return tuple(sorted((k, v) for k, v in record.values.items() if k not in ("_time", "_value")))


class FakeInflux:
    """Answers the two queries the service issues the way Flux would."""

    def __init__(self, records):
        self.records = records
        self.queries = []

    async def query(self, flux, org=None):
        self.queries.append(flux)
        if "|> last()" in flux:
            latest = {}
            for record in self.records:
                key = _series_key(record)
                if key not in latest or record.get_time() > latest[key].get_time():
                    latest[key] = record
            return [_table(latest.values())]
        rows = list(self.records)
        if 'r._level != "ok"' in flux:
            rows = [r for r in rows if r.values["_level"] != "ok"]
        if "r._level == " in flux:
            rows = [r for r in rows if f'r._level == "{r.values["_level"]}"' in flux]
        rows.sort(key=lambda r: r.get_time(), reverse=True)
        return [_table(rows)]


def _table(records):
    table = FluxTable()
    table.records = list(records)
    return table


def fetch(records, **params):
    fake = FakeInflux(records)
    client = MagicMock()
    client.close = AsyncMock()
    client.query_api.return_value = fake
    with patch.object(svc, "get_connector_info_from_db", AsyncMock(return_value={"connector": "InfluxDB"})), patch.object(
        svc,
        "get_influxdb_organization",
        AsyncMock(return_value="SOCFORTRESS"),
    ), patch.object(svc, "create_influxdb_client", AsyncMock(return_value=client)):
        response = asyncio.run(svc.get_influxdb_alerts(GetInfluxDBAlertQueryParams(**params), session=None))
    assert response.success, response.message
    return response, fake.queries


def summary(response):
    return [(a.time.strftime("%H:%M"), a.severity, a.status) for a in response.alerts]


# The reporter's case: wazuh-manager failed at 09:00, recovered at 09:05.
RECOVERED = [
    service("09:00", "soc-wzmas01", "wazuh-manager.service", "crit", active="failed", sub="failed"),
    service("09:05", "soc-wzmas01", "wazuh-manager.service", "ok"),
]


# ── the reported behaviour ──────────────────────────────────────────────────


def test_a_crit_followed_by_an_ok_is_history_not_active():
    response, _ = fetch(RECOVERED)
    assert summary(response) == [("09:05", "ok", "cleared"), ("09:00", "critical", "cleared")]
    assert response.active_alerts_count == 0


def test_overview_query_does_not_report_a_recovered_failure():
    """days=1 + status=active + exclude_ok is what the Overview card and nav badge send."""
    response, _ = fetch(RECOVERED, days=1, status=AlertStatus.ACTIVE, exclude_ok=True, latest_only=True)
    assert response.alerts == []

    response, _ = fetch(RECOVERED, days=1, status=AlertStatus.ACTIVE, exclude_ok=True)
    assert response.alerts == []


def test_exclude_ok_hides_ok_rows_but_still_sees_the_recovery():
    response, queries = fetch(RECOVERED, exclude_ok=True)
    assert summary(response) == [("09:00", "critical", "cleared")]
    state_query = next(q for q in queries if "|> last()" in q)
    assert "_level" not in state_query.split("exists r._level")[1], "state must be computed from every level"


def test_a_failure_that_has_not_recovered_stays_active():
    records = [
        service("09:00", "soc-wzmas01", "wazuh-manager.service", "crit", active="failed", sub="failed"),
        service("09:06", "soc-wzmas01", "wazuh-manager.service", "crit", active="failed", sub="failed"),
    ]
    response, _ = fetch(records, status=AlertStatus.ACTIVE)
    assert summary(response) == [("09:06", "critical", "active"), ("09:00", "critical", "active")]


# ── identity: one check covers many hosts and units ────────────────────────


def test_a_siblings_ok_does_not_hide_a_service_that_is_still_down():
    """Per-_check_id state let graylog's routine OK mark wazuh-manager's live outage cleared."""
    records = [
        service("09:00", "soc-wzmas01", "wazuh-manager.service", "crit", active="failed", sub="failed"),
        service("09:06", "soc-wzmas01", "wazuh-manager.service", "crit", active="failed", sub="failed"),
        service("09:07", "soc-graylog01", "graylog-server.service", "ok"),
    ]
    response, _ = fetch(records, status=AlertStatus.ACTIVE)
    assert [a.status for a in response.alerts] == ["active", "active"]
    assert all("wazuh-manager" in a.message for a in response.alerts)


def test_a_siblings_failure_does_not_reactivate_a_recovered_service():
    records = RECOVERED + [service("09:07", "soc-graylog01", "graylog-server.service", "crit", active="failed", sub="failed")]
    response, _ = fetch(records, status=AlertStatus.ACTIVE)
    assert [(a.time.strftime("%H:%M"), a.status) for a in response.alerts] == [("09:07", "active")]


def test_the_same_unit_on_two_hosts_is_two_things():
    records = [
        service("09:00", "soc-wzmas01", "wazuh-manager.service", "crit", active="failed", sub="failed"),
        service("09:05", "soc-wzmas02", "wazuh-manager.service", "ok"),
    ]
    response, _ = fetch(records, status=AlertStatus.ACTIVE)
    assert summary(response) == [("09:00", "critical", "active")]


def test_latest_only_returns_one_row_per_monitored_thing_not_per_check():
    records = RECOVERED + [
        service("09:01", "soc-graylog01", "graylog-server.service", "ok"),
        service("09:02", "soc-graylog01", "mongod.service", "crit", active="failed", sub="failed"),
        host_offline("09:03", "soc-graylog01", "crit"),
        host_offline("09:04", "soc-graylog01", "ok"),
    ]
    response, _ = fetch(records, latest_only=True)
    assert summary(response) == [
        ("09:05", "ok", "cleared"),  # wazuh-manager: failed then recovered, one entry
        ("09:04", "ok", "cleared"),  # host offline: one entry
        ("09:02", "critical", "active"),  # mongod: still down
        ("09:01", "ok", "cleared"),  # graylog-server
    ]


def test_sidebar_query_lists_exactly_what_is_failing_now():
    records = RECOVERED + [
        service("09:01", "soc-graylog01", "mongod.service", "crit", active="failed", sub="failed"),
        service("09:02", "soc-graylog01", "mongod.service", "crit", active="failed", sub="failed"),
    ]
    response, _ = fetch(records, days=1, status=AlertStatus.ACTIVE, exclude_ok=True, latest_only=True, limit=200)
    assert summary(response) == [("09:02", "critical", "active")]


def test_series_identity_ignores_level_and_state_tags():
    failed = service("09:00", "h", "x.service", "crit", active="failed", sub="failed").values
    running = service("09:05", "h", "x.service", "ok", active="active", sub="running").values
    assert svc.series_identity(failed) == svc.series_identity(running)

    rw = _record("09:00", "disk", "DISK USAGE CHECK", "crit", host="h", path="/", device="sda1", mode="rw").values
    ro = _record("09:05", "disk", "DISK USAGE CHECK", "ok", host="h", path="/", device="sda1", mode="ro").values
    other_path = _record("09:05", "disk", "DISK USAGE CHECK", "ok", host="h", path="/var", device="sda2", mode="rw").values
    assert svc.series_identity(rw) == svc.series_identity(ro)
    assert svc.series_identity(rw) != svc.series_identity(other_path)


def test_severity_filter_does_not_decide_state():
    response, _ = fetch(RECOVERED, severity=[SeverityFilter.CRITICAL])
    assert summary(response) == [("09:00", "critical", "cleared")]


# ── the Flux the service sends ─────────────────────────────────────────────


def test_rows_query_sorts_and_limits_across_series_not_within_each():
    """sort/limit act per table and each series is a table; without group() limit=5 returned 6
    rows on the dev stack, with an older CRIT above a newer OK."""
    _, queries = fetch(RECOVERED, limit=5)
    rows_query = next(q for q in queries if "|> last()" not in q)
    assert rows_query.index("|> group()") < rows_query.index("|> sort(") < rows_query.index("|> limit(n: 5)")


def test_caller_text_cannot_break_out_of_the_query():
    hostile = 'x/) or true or (r._x =~ /" ${string(v: 1)} \\'
    _, queries = fetch(RECOVERED, check_name=hostile, sensor_type=hostile)
    for query in queries:
        assert "r._check_name =~ /" not in query, "caller text must not be spliced into a regex literal"
        assert "regexp.quoteMeta(v: " + svc.flux_string(hostile) + ")" in query


def test_flux_string_escapes_quotes_backslashes_and_interpolation():
    assert svc.flux_string("CPU CHECK") == '"CPU CHECK"'
    assert svc.flux_string('a"b') == '"a\\"b"'
    assert svc.flux_string("a\\b") == '"a\\\\b"'
    assert svc.flux_string("${x}") == '"\\${x}"'


# ── the sidebar indicator ───────────────────────────────────────────────────


def test_sidebar_counts_warnings():
    """The service reports Influx `warn` as `warning`; the indicator only matched "warn"."""
    from app.status.services import context_indicators as indicators

    warning = InfluxDBAlert(
        time=datetime.now(timezone.utc),
        check_name="DISK USAGE CHECK",
        sensor_type="DISK",
        severity="warning",
        message="m",
    )
    response = InfluxDBAlertResponse(success=True, message="ok", alerts=[warning], total_count=1, filtered_count=1)
    with patch.object(indicators, "get_influxdb_alerts", AsyncMock(return_value=response)):
        indicator = asyncio.run(indicators._build_influx_health_indicator(SimpleNamespace()))
    assert (indicator.status, indicator.count) == ("warning", 1)
