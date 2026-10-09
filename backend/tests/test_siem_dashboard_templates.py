"""The built-in SIEM dashboard templates under `app/siem/dashboard_templates/`.

Templates are plain JSON read at request time, so a malformed one only shows up when somebody opens
it: a 500 on the category, or a panel that renders an error. These tests load every category and
template the way `services/dashboards.py` does and pin what the executor and both dashboard viewers
rely on.

The AWS category gets two extra checks. Each of its panels is scoped by `data_aws_source`, so a
CloudTrail dashboard enabled on an event source that also covers GuardDuty (or the other way round)
still shows only its own service. And `data_aws_severity` is a keyword, so GuardDuty severity bands
must not use a numeric range — on a keyword, `[7 TO 10]` compares strings and matches nothing.

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
