"""The built-in SIEM dashboard templates under `app/siem/dashboard_templates/`.

Templates are plain JSON read at request time, so a malformed one only shows up when somebody opens
it: a 500 on the category, or a panel that renders an error. These tests load every category and
template the way `services/dashboards.py` does and pin what the executor and both dashboard viewers
rely on.

The AWS category gets two extra checks. Each of its panels is scoped by `data_aws_source`, so a
CloudTrail dashboard enabled on an event source that also covers GuardDuty (or the other way round)
still shows only its own service. And `data_aws_severity` is a keyword, so GuardDuty severity bands
must not use a numeric range — on a keyword, `[7 TO 10]` compares strings and matches nothing.

The SonicWall category's panels are scoped by `syslog_type:sonicwall`, may only read fields the
SonicWall network connector produces, and leave TCP connection teardown out wherever they rank
hosts by dropped traffic.

No DB, no network.

Run with: cd backend && python -m pytest tests/test_siem_dashboard_templates.py
"""

import json
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.siem.schema.dashboards import DashboardCategory  # noqa: E402
from app.siem.schema.dashboards import DashboardTemplate  # noqa: E402
from app.siem.services.dashboards import get_category_detail  # noqa: E402
from app.siem.services.dashboards import list_categories  # noqa: E402

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "app" / "siem" / "dashboard_templates"
PANEL_TYPES = {"stat", "histogram", "pie", "bar_h", "table"}

CATEGORY_DIRS = sorted(path for path in TEMPLATES_DIR.iterdir() if path.is_dir() and (path / "_card.json").exists())
TEMPLATE_FILES = sorted(path for category in CATEGORY_DIRS for path in category.glob("*.json") if not path.name.startswith("_"))


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_custom_is_not_a_built_in_category():
    """`custom` addresses custom dashboards; a directory with that name would collide with them."""
    assert not (TEMPLATES_DIR / "custom").exists()


@pytest.mark.parametrize("category", CATEGORY_DIRS, ids=lambda p: p.name)
def test_every_card_is_valid_and_named_after_its_directory(category):
    card = DashboardCategory(**load(category / "_card.json"))

    assert card.id == category.name


@pytest.mark.parametrize("path", TEMPLATE_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_every_template_is_well_formed(path):
    template = DashboardTemplate(**load(path))

    assert template.id == path.stem, "the template id is the file stem: that is how enabled dashboards find it"
    ids = [panel.id for panel in template.panels]
    assert len(ids) == len(set(ids)), "panel ids key the panel-data results, so they must be unique"
    for panel in template.panels:
        assert panel.type in PANEL_TYPES, f"{panel.id}: unknown panel type {panel.type}"
        assert 1 <= panel.w <= 12, f"{panel.id}: width is in grid columns (1–12)"
        assert panel.lucene.strip(), f"{panel.id}: empty query"
        if panel.type in ("pie", "bar_h"):
            assert panel.field, f"{panel.id}: an aggregation panel needs `field`"
        if panel.type == "table":
            assert panel.fields, f"{panel.id}: a table panel needs `fields`"


@pytest.mark.parametrize("category", CATEGORY_DIRS, ids=lambda p: p.name)
def test_every_category_loads_through_the_service(category):
    detail = get_category_detail(category.name)

    assert detail.templates, f"{category.name} has no templates"


def test_the_aws_category_is_listed():
    assert "aws_cloudintegration" in {category.id for category in list_categories()}


AWS_TEMPLATES = [path for path in TEMPLATE_FILES if path.parent.name == "aws_cloudintegration"]


@pytest.mark.parametrize("path", AWS_TEMPLATES, ids=lambda p: p.stem)
def test_every_aws_panel_is_scoped_to_its_own_service(path):
    service = "cloudtrail" if "CLOUDTRAIL" in path.stem else "guardduty"

    for panel in load(path)["panels"]:
        assert panel["lucene"].startswith(f"data_aws_source:{service}"), f"{panel['id']} is not scoped to {service}"


def test_guardduty_severity_bands_never_use_a_numeric_range_on_the_keyword():
    for path in AWS_TEMPLATES:
        for panel in load(path)["panels"]:
            assert not re.search(r"data_aws_severity:[\[{]", panel["lucene"]), f"{path.stem}/{panel['id']} ranges over a keyword"


@pytest.mark.parametrize(
    "severity, band",
    [("2", None), ("3.9", None), ("4", "medium"), ("5.5", "medium"), ("7", "high"), ("8.9", "high"), ("9", "critical"), ("10", "critical")],
)
def test_guardduty_severity_bands_match_aws_ranges(severity, band):
    """The bands' regular expressions, applied the way Lucene does (anchored, whole value)."""
    panels = {
        panel["id"]: panel["lucene"] for panel in load(TEMPLATES_DIR / "aws_cloudintegration" / "AWS_GUARDDUTY_SUMMARY.json")["panels"]
    }
    bands = {name: re.search(r"data_aws_severity:/(.+)/$", panels[f"{name}_findings"]).group(1) for name in ("medium", "high", "critical")}

    matched = [name for name, pattern in bands.items() if re.fullmatch(pattern, severity)]

    assert matched == ([band] if band else [])


# ── SonicWall ────────────────────────────────────────────────────────

SONICWALL_TEMPLATES = [path for path in TEMPLATE_FILES if path.parent.name == "sonicwall_firewall"]

# What a SonicWall event carries once the SonicWall network connector's input and pipeline have
# processed it: Graylog's own fields, the syslog level the pipeline names, the fields the UDP
# input's extractors derive, and SonicWall's own key=value pairs.
SONICWALL_FIELDS = {
    "timestamp",
    "syslog_type",
    "syslog_customer",
    "level",
    "syslog_level",
    "src_ip",
    "dst_ip",
    "msg_cat",
    "msg_detail",
    "m",
    "msg",
    "fw",
    "fw_action",
    "gcat",
    "src",
    "dst",
    "srcZone",
    "dstZone",
    "proto",
    "rule",
    "note",
    "usr",
    "sess",
    "ipscat",
    "ipspri",
    "appcat",
    "vpnpolicy",
    "grpName",
    "oldValue",
    "newValue",
}


def lucene_fields(lucene: str) -> set:
    """The fields a Lucene query names, `_exists_:field` included."""
    named = set(re.findall(r"(?<![\w.])([A-Za-z_]\w*):", lucene))
    return (named - {"_exists_"}) | set(re.findall(r"_exists_:(\w+)", lucene))


def test_the_sonicwall_category_is_listed():
    assert "sonicwall_firewall" in {category.id for category in list_categories()}
    assert SONICWALL_TEMPLATES


@pytest.mark.parametrize("path", SONICWALL_TEMPLATES, ids=lambda p: p.stem)
def test_every_sonicwall_panel_is_scoped_to_sonicwall_events(path):
    """So a dashboard enabled on an event source that also covers other indices shows only SonicWall."""
    for panel in load(path)["panels"]:
        assert panel["lucene"].startswith("syslog_type:sonicwall"), f"{panel['id']} is not scoped to SonicWall"


@pytest.mark.parametrize("path", SONICWALL_TEMPLATES, ids=lambda p: p.stem)
def test_every_sonicwall_panel_reads_fields_the_connector_produces(path):
    """A misspelt field is no error to the indexer: the panel just stays empty forever."""
    for panel in load(path)["panels"]:
        read = lucene_fields(panel["lucene"]) | set(filter(None, [panel.get("field")])) | set(panel.get("fields") or [])
        unknown = read - SONICWALL_FIELDS
        assert not unknown, f"{path.stem}/{panel['id']} reads {sorted(unknown)}"


def test_hosts_ranked_by_dropped_traffic_leave_tcp_teardown_out():
    """SonicOS logs each RST or late packet of a closing connection as a drop (events 712 and 713),
    with the zones of the connection and the addresses of the packet: a server's reset to a LAN
    client reads LAN to WAN with the server as the source. They are most of the drops, so a panel
    ranking hosts by dropped traffic without excluding them ranks servers that answered."""
    for path in SONICWALL_TEMPLATES:
        for panel in load(path)["panels"]:
            if "fw_action:drop" in panel["lucene"] and panel.get("field") in ("src_ip", "dst_ip"):
                assert "NOT m:(712 OR 713)" in panel["lucene"], f"{path.stem}/{panel['id']}"
