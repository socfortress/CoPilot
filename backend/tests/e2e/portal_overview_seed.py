"""Seed data for the Customer Portal Overview end-to-end tests (#1181).

Shared by ``customer_portal_overview_e2e.py`` (API level) and the portal's Cypress
specs (browser level), so both assert against the same known rows. Run it
directly to (re)seed or clean the disposable e2e database:

    .venv/bin/python tests/e2e/portal_overview_seed.py seed      # prints JSON for Cypress
    .venv/bin/python tests/e2e/portal_overview_seed.py cleanup

Points at MYSQL_URL (default: the throwaway instance on 127.0.0.1:13306), never at
the MySQL in .env unless you export it yourself.
"""

import asyncio
import datetime
import json
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import AiAnalystJob  # noqa: E402
from app.db.universal_models import AiAnalystReport  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertContext  # noqa: E402
from app.incidents.models import Asset  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402

CUST_A, CUST_B = "E2E_OV_A", "E2E_OV_B"
PORTAL_USER = "e2e_ov_portal"  # customer_user assigned to E2E_OV_A
ADMIN = "e2e_ov_admin"
CONTEXT_SOURCE = "e2e_overview"
PASSWORD = "E2ePassw0rd!x"

# What the portal user must see (E2E_OV_A only), straight from the seed below.
ALERTS_A = ["OPEN", "OPEN", "OPEN", "IN_PROGRESS", "IN_PROGRESS", "CLOSED"]
ALERTS_B = ["OPEN", "OPEN", "CLOSED", "CLOSED"]
CASES_A = ["OPEN", "OPEN", "CLOSED"]
CASES_B = ["OPEN"]
AGENTS_A = [("active", True), ("active", False), ("disconnected", False)]  # (wazuh status, critical)
AGENTS_B = [("active", False)]

NOW = datetime.datetime(2026, 9, 1, 12, 0, 0)


def status_counts(statuses):
    return {
        "total": len(statuses),
        "open": statuses.count("OPEN"),
        "in_progress": statuses.count("IN_PROGRESS"),
        "closed": statuses.count("CLOSED"),
    }


async def cleanup(s):
    codes = [CUST_A, CUST_B]
    alert_ids = select(Alert.id).where(Alert.customer_code.in_(codes))
    case_ids = select(Case.id).where(Case.customer_code.in_(codes))
    await s.execute(delete(AiAnalystReport).where(AiAnalystReport.customer_code.in_(codes)))
    await s.execute(delete(AiAnalystJob).where(AiAnalystJob.customer_code.in_(codes)))
    await s.execute(delete(CustomerPortalAiReportSettings).where(CustomerPortalAiReportSettings.customer_code.in_(codes)))
    await s.execute(delete(CustomerPortalBranding).where(CustomerPortalBranding.customer_code.in_(codes)))
    await s.execute(delete(CaseAlertLink).where(CaseAlertLink.case_id.in_(case_ids)))
    await s.execute(delete(Case).where(Case.customer_code.in_(codes)))
    await s.execute(delete(Asset).where(Asset.alert_linked.in_(alert_ids)))
    await s.execute(delete(Alert).where(Alert.customer_code.in_(codes)))
    await s.execute(delete(AlertContext).where(AlertContext.source == CONTEXT_SOURCE))
    await s.execute(delete(Agents).where(Agents.customer_code.in_(codes)))
    for username in (PORTAL_USER, ADMIN):
        user = (await s.execute(select(User).where(User.username == username))).scalars().first()
        if user:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user.id))
            await s.delete(user)
    await s.execute(delete(Customers).where(Customers.customer_code.in_(codes)))
    await s.commit()


async def seed(quiet: bool = False) -> int:
    # expire_on_commit=False: the seed reads ids of rows it just committed, and an
    # expired attribute would trigger a synchronous refresh (MissingGreenlet).
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        for role_id, name in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == role_id))).scalars().first():
                s.add(Role(id=role_id, name=name, description=name))
        await s.commit()
        await cleanup(s)

        for code in (CUST_A, CUST_B):
            s.add(Customers(customer_code=code, customer_name=f"Customer {code}", customer_type="MSSP", logo_file=""))
        context = AlertContext(source=CONTEXT_SOURCE, context={})
        s.add(context)
        await s.commit()

        alerts = {}
        minute = 0
        for code, statuses in ((CUST_A, ALERTS_A), (CUST_B, ALERTS_B)):
            for i, status in enumerate(statuses):
                minute += 1
                alert = Alert(
                    alert_name=f"{code} alert {i}",
                    alert_description=f"{code} alert {i} description" if i % 2 else f"{code} alert {i}",
                    status=status,
                    alert_creation_time=NOW + datetime.timedelta(minutes=minute),
                    customer_code=code,
                    source="wazuh",
                )
                s.add(alert)
                alerts[(code, i)] = alert
        await s.commit()

        # Two assets on one alert, one on another: the Overview shows "first +N".
        for (code, i), names in {(CUST_A, 0): ["host-a1", "host-a2"], (CUST_A, 1): ["host-a3"], (CUST_B, 0): ["host-b1"]}.items():
            for name in names:
                s.add(
                    Asset(
                        alert_linked=alerts[(code, i)].id,
                        asset_name=name,
                        alert_context_id=context.id,
                        customer_code=code,
                        index_name="e2e",
                        index_id=f"{code}-{i}-{name}",
                    ),
                )

        cases = {}
        for code, statuses in ((CUST_A, CASES_A), (CUST_B, CASES_B)):
            for i, status in enumerate(statuses):
                case = Case(
                    case_name=f"{code} case {i}",
                    case_description=f"{code} case {i}",
                    case_status=status,
                    case_creation_time=NOW + datetime.timedelta(hours=i),
                    customer_code=code,
                    assigned_to="analyst1" if i == 0 else None,
                )
                s.add(case)
                cases[(code, i)] = case
        await s.commit()
        # The first case of A links two alerts, so its row reads "2 alerts".
        for i in (0, 1):
            s.add(CaseAlertLink(case_id=cases[(CUST_A, 0)].id, alert_id=alerts[(CUST_A, i)].id))

        for code, agents in ((CUST_A, AGENTS_A), (CUST_B, AGENTS_B)):
            for i, (wazuh_status, critical) in enumerate(agents):
                s.add(
                    Agents(
                        agent_id=f"e2e-ov-{code}-{i}",
                        ip_address=f"10.9.0.{i}",
                        os="Linux",
                        hostname=f"ov-{code}-{i}",
                        label=f"ov-{code}-{i}",
                        critical_asset=critical,
                        customer_code=code,
                        quarantined=False,
                        velociraptor_id="",
                        velociraptor_org="root",
                        wazuh_last_seen=NOW,
                        velociraptor_last_seen=NOW,
                        wazuh_agent_version="4.x",
                        velociraptor_agent_version="0.7",
                        wazuh_agent_status=wazuh_status,
                    ),
                )

        # AI: alert A0 has two reports (only the latest, High, counts), A1 one; B0 one.
        for n, (code, i, severity) in enumerate(
            [(CUST_A, 0, "Low"), (CUST_A, 0, "High"), (CUST_A, 1, "Medium"), (CUST_B, 0, "Critical")],
        ):
            job_id = f"e2e-ov-job-{n}"
            s.add(AiAnalystJob(id=job_id, alert_id=alerts[(code, i)].id, customer_code=code, status="completed", triggered_by="manual"))
            await s.flush()
            s.add(
                AiAnalystReport(
                    job_id=job_id,
                    alert_id=alerts[(code, i)].id,
                    customer_code=code,
                    severity_assessment=severity,
                    summary=f"{severity} finding",
                    created_at=NOW + datetime.timedelta(days=1, minutes=n),
                ),
            )
        for code in (CUST_A, CUST_B):
            s.add(CustomerPortalAiReportSettings(customer_code=code, enabled=True))

        password = AuthHandler().get_password_hash(PASSWORD)
        s.add(User(username=PORTAL_USER, password=password, email=f"{PORTAL_USER}@e2e.local", role_id=4))
        s.add(User(username=ADMIN, password=password, email=f"{ADMIN}@e2e.local", role_id=1))
        await s.commit()
        portal = (await s.execute(select(User).where(User.username == PORTAL_USER))).scalars().first()
        s.add(UserCustomerAccess(user_id=portal.id, customer_code=CUST_A))
        await s.commit()
        if not quiet:
            print(f"seed: {CUST_A} and {CUST_B} with alerts, assets, cases, agents, AI reports; '{PORTAL_USER}' assigned to {CUST_A}")
        return portal.id


def fixture() -> dict:
    """What the tests need to know about the seed, as JSON-friendly data."""
    return {
        "customers": {"a": CUST_A, "b": CUST_B},
        "portal_user": PORTAL_USER,
        "admin": ADMIN,
        "password": PASSWORD,
        "alerts": {"a": status_counts(ALERTS_A), "b": status_counts(ALERTS_B)},
        "cases": {"a": status_counts(CASES_A), "b": status_counts(CASES_B)},
        "agents_a": {
            "total": len(AGENTS_A),
            "online": sum(status == "active" for status, _ in AGENTS_A),
            "critical": sum(critical for _, critical in AGENTS_A),
        },
        "ai_a": {"total_reports": 2, "severity_counts": {"High": 1, "Medium": 1}},
    }


async def _main(command: str) -> None:
    # This deletes and recreates rows: refuse anything but the throwaway instance unless asked.
    if not os.environ["MYSQL_URL"].endswith(":13306") and os.environ.get("E2E_ALLOW_ANY_DB") != "1":
        raise SystemExit(f"Refusing to seed {os.environ['MYSQL_URL']}: not the e2e MySQL on :13306 (set E2E_ALLOW_ANY_DB=1 to override).")
    if command == "seed":
        portal_user_id = await seed(quiet=True)
        print(json.dumps({**fixture(), "portal_user_id": portal_user_id}))
    elif command == "cleanup":
        async with AsyncSession(async_engine) as s:
            await cleanup(s)
    else:
        raise SystemExit(f"unknown command {command!r}: use 'seed' or 'cleanup'")
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else "seed"))
