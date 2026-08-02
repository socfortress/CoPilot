"""Alert severity storage and resolution.

Alerts had no stored severity. It was derived at ingest from the Wazuh rule
level, used for the notification, and discarded — so anything after ingest was
blind to it, and sources carrying no rule level (Office 365, CrowdStrike, Carbon
Black, Huntress) silently resolved to a hardcoded `Medium`. A route gating at
*High and above* dropped every one of them.

The design decision these tests mostly exist to protect: **NULL is resolved at
read time, not stamped at ingest.** That keeps "the source said Medium"
distinguishable from "we guessed", and makes changing the deployment default
take effect immediately — including for alerts already in the database.

Run with: cd backend && python -m pytest tests/test_alert_severity.py
"""

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.incidents.services.alert_severity import FALLBACK_SEVERITY  # noqa: E402
from app.incidents.services.alert_severity import SEVERITY_LEVELS  # noqa: E402
from app.incidents.services.alert_severity import default_severity  # noqa: E402
from app.incidents.services.alert_severity import normalize_severity  # noqa: E402
from app.incidents.services.alert_severity import severity_of  # noqa: E402
from app.incidents.services.alert_severity import severity_rank  # noqa: E402


def _alert(severity=None):
    return SimpleNamespace(id=1, severity=severity)


def _with_default(value):
    return patch.dict(os.environ, {"DEFAULT_ALERT_SEVERITY": value})


def _without_default():
    env = {k: v for k, v in os.environ.items() if k != "DEFAULT_ALERT_SEVERITY"}
    return patch.dict(os.environ, env, clear=True)


# ── resolution at read time ───────────────────────────────────────────────


def test_a_stored_severity_is_used():
    assert severity_of(_alert("Critical")) == "Critical"


def test_null_resolves_to_the_deployment_default():
    """NULL means "the source didn't say", not "unimportant"."""
    with _without_default():
        assert severity_of(_alert(None)) == FALLBACK_SEVERITY


def test_changing_the_default_changes_existing_alerts_immediately():
    """The reason NULL isn't stamped at ingest. If the fallback were written to
    the row, changing this setting would only affect alerts created afterwards
    and would need a backfill to apply retroactively."""
    alert = _alert(None)
    with _with_default("Critical"):
        assert severity_of(alert) == "Critical"
    with _with_default("Low"):
        assert severity_of(alert) == "Low"


def test_a_stored_value_is_not_overridden_by_the_default():
    with _with_default("Critical"):
        assert severity_of(_alert("Low")) == "Low"


# ── the default ───────────────────────────────────────────────────────────


def test_the_shipped_default_is_high():
    """High rather than Critical: loud enough that an unmapped source is never
    silently suppressed, while leaving "Critical only" a filter that still means
    something. A blanket Critical would also remove the main brake on the Resend
    monthly quota."""
    with _without_default():
        assert default_severity() == "High"
    assert FALLBACK_SEVERITY == "High"


@pytest.mark.parametrize("level", SEVERITY_LEVELS)
def test_every_level_is_configurable(level):
    with _with_default(level):
        assert default_severity() == level


def test_the_setting_is_case_insensitive():
    with _with_default("critical"):
        assert default_severity() == "Critical"


def test_a_typo_in_the_setting_falls_back_rather_than_breaking_ingest():
    """A bad environment variable must not take down alert creation."""
    with _with_default("Sevre"):
        assert default_severity() == FALLBACK_SEVERITY


def test_an_empty_setting_falls_back():
    with _with_default(""):
        assert default_severity() == FALLBACK_SEVERITY


# ── normalisation ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw", ["critical", "CRITICAL", " Critical ", "Critical"])
def test_sources_are_inconsistent_about_case_and_whitespace(raw):
    assert normalize_severity(raw) == "Critical"


@pytest.mark.parametrize("raw", [None, "", "Sev1", "urgent", "9"])
def test_an_unrecognised_value_becomes_null_rather_than_being_stored(raw):
    """Better to store NULL and resolve to the default than persist something
    nothing can filter on."""
    assert normalize_severity(raw) is None


# ── ranking ───────────────────────────────────────────────────────────────


def test_levels_rank_in_order():
    ranks = [severity_rank(level) for level in SEVERITY_LEVELS]
    assert ranks == sorted(ranks)
    assert severity_rank("Critical") > severity_rank("High") > severity_rank("Informational")


def test_an_unknown_severity_ranks_below_everything():
    """Which is exactly why callers must rank `severity_of(alert)` and not
    `alert.severity` — passing the raw NULL would drop the alert from every
    filter, the bug this module exists to fix."""
    assert severity_rank(None) < severity_rank("Informational")


def test_ranking_the_resolved_value_puts_a_null_alert_above_informational():
    with _without_default():
        assert severity_rank(severity_of(_alert(None))) > severity_rank("Informational")


# ── the reported bug ──────────────────────────────────────────────────────


def test_a_non_wazuh_alert_is_not_dropped_by_a_high_gate():
    """The concrete failure: a CrowdStrike alert has no rule level, stored NULL,
    and previously resolved to Medium — so a route gating at High never saw it.
    """
    crowdstrike_alert = _alert(None)
    with _without_default():
        assert severity_rank(severity_of(crowdstrike_alert)) >= severity_rank("High")
