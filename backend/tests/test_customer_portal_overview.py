"""``GET /customer_portal/overview``: one call for the whole portal Overview.

Pins the two things the four separate calls gave for free and a single call could
lose: sections fail independently, and alert visibility — built once — reaches every
alert-based section.

Run with: cd backend && python -m pytest tests/test_customer_portal_overview.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_portal.services.overview as overview  # noqa: E402
from app.customer_portal.schema.overview import OverviewAgentsSection  # noqa: E402
from app.customer_portal.schema.overview import OverviewAiSection  # noqa: E402
from app.customer_portal.schema.overview import OverviewAlertsSection  # noqa: E402
from app.customer_portal.schema.overview import OverviewCasesSection  # noqa: E402

USER = SimpleNamespace(id=1, username="customer1", role_id=4)
VISIBILITY = ["<visibility>"]


def _run(**overrides):
    sections = {
        "alert_visibility_filters_for_user": AsyncMock(return_value=VISIBILITY),
        "_alerts_section": AsyncMock(return_value=OverviewAlertsSection()),
        "_cases_section": AsyncMock(return_value=OverviewCasesSection()),
        "_agents_section": AsyncMock(return_value=OverviewAgentsSection(total=3)),
        "_ai_section": AsyncMock(return_value=OverviewAiSection()),
        **overrides,
    }
    session = AsyncMock()
    with patch.multiple(overview, **sections):
        result = asyncio.run(overview.get_portal_overview(USER, session))
    return result, sections, session


def test_visibility_is_built_once_and_shared():
    _, sections, _ = _run()
    sections["alert_visibility_filters_for_user"].assert_awaited_once()
    assert sections["_alerts_section"].await_args.args[1] is VISIBILITY
    assert sections["_ai_section"].await_args.args[1] is VISIBILITY


def test_a_failing_section_does_not_blank_the_others():
    result, _, session = _run(_cases_section=AsyncMock(side_effect=RuntimeError("db down")))
    assert result.cases.error == "Failed to load cases"
    assert result.agents.total == 3 and result.agents.error is None
    assert result.alerts.error is None and result.ai.error is None
    # The failed transaction is rolled back so the sections after it can still query.
    session.rollback.assert_awaited_once()


def test_errors_never_leak_internals():
    result, _, _ = _run(_agents_section=AsyncMock(side_effect=RuntimeError("password=hunter2 at 10.0.0.1")))
    assert result.agents.error == "Failed to load agents"


def test_visibility_failure_marks_only_the_alert_based_sections():
    result, sections, _ = _run(alert_visibility_filters_for_user=AsyncMock(side_effect=RuntimeError("tags table gone")))
    assert result.alerts.error and result.ai.error
    assert result.cases.error is None and result.agents.error is None
    sections["_alerts_section"].assert_not_awaited()
    sections["_ai_section"].assert_not_awaited()


def test_a_user_who_sees_no_alerts_gets_empty_sections_not_errors():
    result = asyncio.run(overview._alerts_section(AsyncMock(), None, 6))
    assert result == OverviewAlertsSection()
    assert asyncio.run(overview._ai_section(AsyncMock(), None, 3)) == OverviewAiSection()
