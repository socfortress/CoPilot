"""The SLA section of the customer PDF report (#1187).

- It is opt-in: absent unless the request asks for it.
- A portal user cannot ask for it: SLA figures reach a customer only through a report
  the SOC chose to include them in.
- When included, the templates render it (and never an analyst's name).

Run with: cd backend && python -m pytest tests/test_customer_report_sla.py
"""

import asyncio
import json
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.routes.customer_report as routes  # noqa: E402
import app.incidents.services.customer_report as service  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.schema.customer_report import (  # noqa: E402
    CustomerReportGenerateRequest,
)
from app.incidents.services.customer_report_branding import (  # noqa: E402
    _socfortress_theme,
)
from tests.soc_management_support import Db  # noqa: E402

PORTAL = SimpleNamespace(id=10, username="portal", role_id=4)
ANALYST = SimpleNamespace(id=2, username="ana", role_id=2)


def _request(**overrides):
    data = {"customer_code": "ACME", "date_from": datetime(2026, 9, 1), "date_to": datetime(2026, 10, 1), "include_sla": True}
    return CustomerReportGenerateRequest(**{**data, **overrides})


def test_include_sla_defaults_to_off():
    assert (
        CustomerReportGenerateRequest(customer_code="A", date_from=datetime(2026, 9, 1), date_to=datetime(2026, 9, 2)).include_sla is False
    )


def _queue(user):
    """Run the generate route; return the placeholder row and the request handed to the generator."""
    session = AsyncMock()
    session.add = MagicMock()
    found = MagicMock()
    found.scalars.return_value.first.return_value = SimpleNamespace(customer_code="ACME")
    session.execute = AsyncMock(return_value=found)

    async def refresh(row):
        row.id = 1

    session.refresh = refresh
    tasks = MagicMock()
    with patch.object(routes, "_ensure_customer_access", AsyncMock()):
        asyncio.run(routes.generate_report_background(_request(), tasks, user, session))
    row = session.add.call_args.args[0]
    return row, tasks


def test_a_portal_user_cannot_include_sla_figures():
    row, _ = _queue(PORTAL)
    assert json.loads(row.filters_json)["include_sla"] is False


def test_the_soc_can_include_sla_figures():
    row, _ = _queue(ANALYST)
    assert json.loads(row.filters_json)["include_sla"] is True


def _context(include_sla):
    async def _inner():
        db = await Db().create()
        try:
            async with db.session() as session:
                customer = Customers(customer_code="ACME", customer_name="Acme Corp")
                session.add(customer)
                await session.commit()
                fake_sla = AsyncMock(return_value={"has_data": False, "tracking_since": None})
                with patch.object(service, "resolve_theme", AsyncMock(return_value=_socfortress_theme())), patch(
                    "app.soc_management.services.report.customer_sla_context",
                    fake_sla,
                ):
                    context = await service.build_report_context(session, customer, _request(include_sla=include_sla))
                return context, fake_sla
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def test_the_context_carries_the_sla_section_only_when_asked():
    without, fake = _context(False)
    assert without["sla"] is None and not fake.await_count
    with_sla, fake = _context(True)
    assert with_sla["sla"] == {"has_data": False, "tracking_since": None}
    fake.assert_awaited_once()


def test_every_metrics_template_renders_the_section_and_operational_does_not():
    from jinja2 import FileSystemLoader
    from jinja2 import select_autoescape
    from jinja2.sandbox import SandboxedEnvironment

    context, _ = _context(False)
    context["sla"] = {
        "has_data": True,
        "tracking_since": "2026-09-01",
        "alerts": {
            "opened": 3,
            "tta_median": "12m",
            "ttr_median": "2h",
            "ack": {"rate": "100.0%", "cls": "rate-good", "width": 100},
            "resolve": {"rate": "66.7%", "cls": "rate-bad", "width": 66.7},
        },
        "cases": {"opened": 0},
        "alert_severities": [
            {
                "severity": "High",
                "ack_target": "1h",
                "resolve_target": "8h",
                "opened": 3,
                "empty": False,
                "tta": "12m",
                "ttr": "2h",
                "ack": {"rate": "100.0%", "cls": "rate-good", "width": 100},
                "resolve": {"rate": "66.7%", "cls": "rate-bad", "width": 66.7},
                "open_now": 1,
                "breached_now": 1,
            },
        ],
        "case_severities": [],
    }
    env = SandboxedEnvironment(loader=FileSystemLoader(service.TEMPLATE_DIR), autoescape=select_autoescape(default=True))
    for layout in ("full", "executive", "analytics"):
        html = env.get_template(service.TEMPLATE_FILES[layout]).render(context)
        assert "Service Level Performance" in html, layout
        assert "66.7%" in html
    operational = env.get_template(service.TEMPLATE_FILES["operational"]).render(context)
    assert "Service Level Performance" not in operational
