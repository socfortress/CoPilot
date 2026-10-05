"""The Customer Portal SLA service (#1187), below the HTTP layer.

`test_customer_portal_sla.py` drives the routes end to end; this pins the two pieces of
`app/customer_portal/services/sla.py` that decide what a customer reads:

- `project()` — the pure projection of the analyst dashboard's snapshot into the portal
  schema: which targets are listed, how the trend and "open now" are folded, and that no
  person can appear (there is no field to carry one);
- `enabled_customer_codes()` — the caller's customers, narrowed to the enabled ones
  (and to the ones they asked for) before anything is computed.

Run with: cd backend && python -m pytest tests/test_customer_portal_sla_service.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.customer_portal.services import sla as sla_service  # noqa: E402
from app.db.universal_models import CustomerPortalSlaSettings  # noqa: E402
from app.soc_management.domain.analytics import AssigneeLoad  # noqa: E402
from app.soc_management.domain.analytics import EntityHeadline  # noqa: E402
from app.soc_management.domain.analytics import Headline  # noqa: E402
from app.soc_management.domain.analytics import SeverityRow  # noqa: E402
from app.soc_management.domain.analytics import SlaPair  # noqa: E402
from app.soc_management.domain.analytics import TrendPoint  # noqa: E402
from app.soc_management.domain.analytics import Workload  # noqa: E402
from app.soc_management.domain.periods import Bucket  # noqa: E402
from app.soc_management.domain.periods import Period  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.domain.sla import Compliance  # noqa: E402
from app.soc_management.domain.stats import DurationStats  # noqa: E402
from app.soc_management.schema.policy import PolicyCell  # noqa: E402
from app.soc_management.schema.policy import PolicyMatrix  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402

START = datetime(2026, 9, 1)
END = datetime(2026, 10, 1)


def _headline(opened, met, breached, tta=None, ttr=None):
    entity = EntityHeadline(
        opened=opened,
        resolved=met + breached,
        tta=DurationStats(count=1, median=tta),
        ttr=DurationStats(count=1, median=ttr),
        sla=SlaPair(ack=Compliance(met=met, breached=breached), resolve=Compliance(met=met)),
    )
    return Headline(
        alerts=entity,
        cases=EntityHeadline(),
        false_positive_rate=None,
        reviewed_alerts=0,
        case_conversion_rate=None,
        escalated_alerts=0,
    )


def _cell(severity, ack, resolve, business_hours=False, entity=SlaEntity.ALERT):
    return PolicyCell(
        entity=entity,
        severity=severity,
        ack_minutes=ack,
        resolve_minutes=resolve,
        business_hours=business_hours,
        source="global",
    )


def _snapshot():
    return SimpleNamespace(
        period=Period(START, END),
        bucket=Bucket.DAY,
        tracking_since=START,
        headline=_headline(10, 8, 2, tta=600.0, ttr=7200.0),
        previous_headline=_headline(5, 5, 0),
        severities=[
            SeverityRow(
                entity=SlaEntity.ALERT,
                severity="High",
                opened=7,
                resolved=6,
                open_now=1,
                breached_now=1,
                tta=DurationStats(),
                ttr=DurationStats(count=6, median=3600.0),
                sla=SlaPair(ack=Compliance(met=6, breached=1), resolve=Compliance(met=5, breached=1)),
            ),
        ],
        trends=[TrendPoint(start=START, alerts_opened=3, alerts_resolved=2, cases_opened=1, cases_resolved=1, sla_rate=75.0)],
        workload=Workload(
            open_alerts=4,
            open_cases=1,
            unassigned_alerts=2,
            unassigned_cases=0,
            waiting_on_customer=2,
            oldest_unassigned_at=None,
            breached=1,
            at_risk=1,
            by_severity=[],
            by_assignee=[AssigneeLoad(username="ana", alerts=4)],
        ),
        policy=PolicyMatrix(
            customer_code="ACME",
            cells=[
                _cell("High", 60, 480, business_hours=True),
                _cell("Low", None, 4320),
                _cell("Informational", None, None),  # no promise: not a commitment worth listing
            ],
        ),
    )


def test_project_lists_the_promises_and_how_they_were_kept():
    page = sla_service.project(_snapshot(), ["ACME"])
    assert page.enabled and page.customer_codes == ["ACME"] and page.bucket == "day"
    assert [(t.severity, t.business_hours) for t in page.targets] == [("High", True), ("Low", False)]
    high = page.targets[0]
    assert (high.acknowledge_minutes, high.resolve_minutes, high.opened) == (60, 480, 7)
    assert (high.acknowledge_rate, high.resolve_rate, high.time_to_resolve) == (85.7, 83.3, 3600.0)
    low = page.targets[1]
    assert low.opened == 0 and low.acknowledge_rate is None  # nothing at that severity this period


def test_project_folds_the_headline_trend_and_backlog():
    page = sla_service.project(_snapshot(), ["ACME"])
    assert page.alerts.acknowledge.model_dump() == {"met": 8, "breached": 2, "rate": 80.0}
    assert (page.alerts.time_to_acknowledge, page.alerts.time_to_resolve) == (600.0, 7200.0)
    assert page.previous_alerts.acknowledge.rate == 100.0
    assert page.cases.acknowledge.rate is None  # no outcome is "—", never 0%
    assert [(p.opened, p.resolved, p.rate) for p in page.trend] == [(4, 3, 75.0)]
    assert page.open_now.model_dump() == {"alerts": 4, "cases": 1, "breached": 1, "at_risk": 1, "waiting_on_you": 2}


def test_project_carries_no_name_even_when_the_snapshot_has_one():
    assert "ana" not in sla_service.project(_snapshot(), ["ACME"]).model_dump_json()


# ── which customers ──────────────────────────────────────────────────────────


def _codes(accessible, requested=None):
    async def scenario():
        db = await Db().create()
        try:
            async with db.session() as session:
                session.add_all(
                    [
                        CustomerPortalSlaSettings(customer_code="ACME", enabled=True),
                        CustomerPortalSlaSettings(customer_code="GLOBEX", enabled=True),
                        CustomerPortalSlaSettings(customer_code="INITECH", enabled=False),
                    ],
                )
                await session.commit()
                with patch.object(sla_service.customer_access_handler, "get_user_accessible_customers", AsyncMock(return_value=accessible)):
                    return await sla_service.enabled_customer_codes(SimpleNamespace(id=9), session, requested)
        finally:
            await db.dispose()

    return asyncio.run(scenario())


def test_only_enabled_customers_the_caller_may_see_are_read():
    assert _codes(["*"]) == ["ACME", "GLOBEX"]  # INITECH is off
    assert _codes(["ACME", "INITECH"]) == ["ACME"]
    assert _codes([]) == []  # a user with no customer sees nothing, not everything


def test_a_requested_subset_narrows_and_never_widens():
    assert _codes(["*"], ["GLOBEX"]) == ["GLOBEX"]
    assert _codes(["ACME"], ["GLOBEX"]) == []
