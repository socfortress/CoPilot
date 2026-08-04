"""Structural guarantees for the provisionable InfluxDB check templates.

The templates under app/stack_provisioning/influxdb/templates/ are literal
`POST /api/v2/checks` request bodies with two placeholders — REPLACE_ORG_ID and
REPLACE_BUCKET — substituted at provisioning time. InfluxDB accepts a payload
that still carries a placeholder (it just creates a check owned by no org, or
one querying a bucket named "REPLACE_BUCKET"), and the failure only shows up
later as a check that silently never fires. So the placeholders, and the
enum <-> template correspondence that drives the whole feature, are asserted
here rather than discovered in production.

No DB, no network — these read the template files off disk.

Run with: cd backend && python -m pytest tests/test_influxdb_check_templates.py
"""

import json
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.stack_provisioning.influxdb.schema.provision import (  # noqa: E402
    AvailableInfluxDBChecks,
)

TEMPLATE_DIR = Path(__file__).parent.parent / "app" / "stack_provisioning" / "influxdb" / "templates"

VALID_LEVELS = {"OK", "INFO", "WARN", "CRIT"}
VALID_THRESHOLD_TYPES = {"greater", "lesser", "range"}


def _load(template_name: str) -> dict:
    return json.loads((TEMPLATE_DIR / f"{template_name}.json").read_text())


def test_every_enum_member_has_a_template():
    """The enum name is the template file stem — a missing file is a 404 at provision time."""
    for check in AvailableInfluxDBChecks:
        assert (TEMPLATE_DIR / f"{check.name}.json").is_file(), f"No template file for {check.name}"


def test_every_template_has_an_enum_member():
    """An orphaned template is unreachable — nothing can request it."""
    member_names = set(AvailableInfluxDBChecks.__members__)
    for template_file in TEMPLATE_DIR.glob("*.json"):
        assert template_file.stem in member_names, f"Template {template_file.name} has no enum member"


def test_enum_descriptions_are_unique():
    """str-Enum members sharing a value are silently aliased, which would drop a check
    from the available list without any error."""
    assert len(set(AvailableInfluxDBChecks.__members__)) == len(list(AvailableInfluxDBChecks))


def test_templates_carry_both_placeholders():
    for check in AvailableInfluxDBChecks:
        template = _load(check.name)
        assert template["orgID"] == "REPLACE_ORG_ID", f"{check.name} does not use the org ID placeholder"
        assert "REPLACE_BUCKET" in template["query"]["text"], f"{check.name} query does not use the bucket placeholder"
        # Builder-mode checks repeat the bucket in builderConfig; the InfluxDB UI reads it
        # from there, so a hardcoded bucket would show the wrong source on the edit screen.
        builder_config = template["query"].get("builderConfig")
        if builder_config is not None:
            assert builder_config["buckets"] == ["REPLACE_BUCKET"], f"{check.name} builderConfig has a hardcoded bucket"


def test_templates_are_well_formed_threshold_checks():
    for check in AvailableInfluxDBChecks:
        template = _load(check.name)
        assert template["type"] == "threshold"
        assert template["status"] == "active"
        assert template["every"], f"{check.name} has no schedule"
        assert template["name"], f"{check.name} has no InfluxDB check name"
        assert "${ r._check_name }" in template["statusMessageTemplate"], f"{check.name} status message omits the check name"

        thresholds = template["thresholds"]
        assert thresholds, f"{check.name} has no thresholds and would never fire"
        for threshold in thresholds:
            assert threshold["level"] in VALID_LEVELS
            assert threshold["type"] in VALID_THRESHOLD_TYPES
            assert isinstance(threshold["value"], (int, float))


def test_influxdb_check_names_are_unique():
    """Provisioning matches existing checks by name, so two templates sharing a name would
    make the second overwrite the first."""
    names = [_load(check.name)["name"] for check in AvailableInfluxDBChecks]
    assert len(names) == len(set(names)), f"Duplicate InfluxDB check names: {names}"


def test_cpu_template_matches_the_hand_built_check():
    """The CPU check already exists on stacks built before CoPilot was pointed at them.
    The template mirrors it exactly so that overwriting is a genuine no-op — if these
    thresholds drift, an overwrite silently re-tunes every existing deployment."""
    template = _load(AvailableInfluxDBChecks.SOCFORTRESS_INFLUXDB_CPU_CHECK.name)
    assert template["name"] == "CPU CHECK"
    assert template["every"] == "1m"
    assert [(t["level"], t["value"], t["type"]) for t in template["thresholds"]] == [
        ("INFO", 25, "lesser"),
        ("WARN", 15, "lesser"),
        ("CRIT", 5, "lesser"),
    ]


"""The units the critical-services check watches.

Adding a unit here is NOT free. Telegraf reports inactive units too, so a unit that is
installed-but-stopped — or that systemd carries as a `not-found` stub because something
else references it — reports active_code=2 and trips the `> 0` CRIT threshold. On a
role-split deployment (soc-grfna01 runs Grafana, not InfluxDB) that is a false critical
alert; influxdb.service was removed from this list for exactly that reason. Only add a
unit that genuinely runs on every host reporting to this InfluxDB.
"""
WATCHED_UNITS = {
    "graylog-server.service",
    "grafana-server.service",
    "mongod.service",
    "nginx.service",
    "socfortress-wazuh-utils.service",
    "socfortress-workerprovisioning.service",
    "telegraf.service",
    "velociraptor_server.service",
    "wazuh-dashboard.service",
    "wazuh-indexer.service",
    "wazuh-manager.service",
    "haproxy.service",
    "fluent-bit.service",
    "docker.service",
}


def test_critical_services_watch_list_is_exactly_the_agreed_set():
    query = _load(AvailableInfluxDBChecks.SOCFORTRESS_INFLUXDB_CRITICAL_SERVICES_CHECK.name)["query"]["text"]
    watched = set(re.findall(r'"name"\]\s*==\s*"([^"]+)"', query))
    assert watched == WATCHED_UNITS


def test_influxdb_service_is_not_watched():
    """Regression for the false CRIT on soc-grfna01: InfluxDB is a single-host role, so
    every other host in the stack reports the unit as inactive or not-found."""
    query = _load(AvailableInfluxDBChecks.SOCFORTRESS_INFLUXDB_CRITICAL_SERVICES_CHECK.name)["query"]["text"]
    assert "influxdb.service" not in query


def test_critical_services_alerts_on_failed_not_on_stopped():
    """The load-bearing assertion for role-split stacks.

    Telegraf's active_code is active=0, reloading=1, inactive=2, failed=3, activating=4,
    deactivating=5. Most watched units are legitimately stopped (2) on any given host
    because no host runs every service, and systemd `not-found` stubs also report 2. A
    `> 0` threshold therefore CRITs on every service a host does not own — which is the
    bug this pins. Only a failed unit (3) may alert.
    """
    thresholds = _load(AvailableInfluxDBChecks.SOCFORTRESS_INFLUXDB_CRITICAL_SERVICES_CHECK.name)["thresholds"]
    assert len(thresholds) == 1
    threshold = thresholds[0]
    assert threshold["level"] == "CRIT"
    assert threshold["type"] == "greater"
    assert threshold["value"] == 2, "an inactive unit (active_code=2) must not raise a critical alert"


@pytest.mark.parametrize(
    ("template_name", "measurement", "field"),
    [
        ("SOCFORTRESS_INFLUXDB_CPU_CHECK", "cpu", "usage_idle"),
        ("SOCFORTRESS_INFLUXDB_MEMORY_CHECK", "mem", "available_percent"),
        ("SOCFORTRESS_INFLUXDB_DISK_CHECK", "disk", "used_percent"),
        ("SOCFORTRESS_INFLUXDB_CRITICAL_SERVICES_CHECK", "systemd_units", "active_code"),
    ],
)
def test_templates_query_the_expected_telegraf_series(template_name, measurement, field):
    """These are the measurement/field pairs Telegraf actually emits on a SOCFortress stack.
    A threshold check whose query returns nothing never alerts and never errors."""
    query = _load(template_name)["query"]["text"]
    assert f'"_measurement"] == "{measurement}"' in query
    assert f'"_field"] == "{field}"' in query
