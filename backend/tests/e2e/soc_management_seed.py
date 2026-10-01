"""Seed data for the SOC Management browser tests (#1187): a month of SOC history.

Shared by the analyst frontend's Playwright spec (``e2e/soc-management.spec.ts``) and by
anyone who wants to look at the page with believable data. Run it directly to (re)seed or
clean the disposable e2e database:

    .venv/bin/python tests/e2e/soc_management_seed.py seed      # prints JSON for Playwright
    .venv/bin/python tests/e2e/soc_management_seed.py cleanup

Points at MYSQL_URL (default: the throwaway instance on 127.0.0.1:13306), never at the
MySQL in .env unless you export it yourself.

**Why the SLA history is written straight to the tables.** Every lifecycle action through
the API is stamped "now", so a month of response and resolution times cannot be produced
through it. The seed therefore writes tracking rows with past timestamps — the same shape
the recorder writes — using a fixed random seed, so every run produces the same history
relative to its own "now". What the API *can* do (a lifecycle action, a policy save, the
tenancy of every read) the browser spec exercises through the UI.
"""

import asyncio
import datetime
import json
import os
import random
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
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import CaseEvent  # noqa: E402
from app.incidents.models import CaseTask  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.soc_management.domain.policy import PolicyRow  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.domain.policy import resolve_targets  # noqa: E402
from app.soc_management.models.sla import AlertSlaTracking  # noqa: E402
from app.soc_management.models.sla import CaseSlaTracking  # noqa: E402
from app.soc_management.models.sla import SlaPolicy  # noqa: E402

CUSTOMERS = {
    "E2E_SLA_A": "Acme Industries",
    "E2E_SLA_B": "Globex Retail",
    "E2E_SLA_C": "Initech Health",
}
ADMIN = "e2e_sla_admin"
SCOPED = "e2e_sla_ana"  # analyst assigned to E2E_SLA_A only
ANALYSTS = ["e2e_sla_bob", "e2e_sla_cleo"]  # unassigned analysts: deployment-wide
PASSWORD = "E2ePlaywr1ght!"
DAYS = 30
RANDOM_SEED = 1187

# (title, source, severity, false-positive share)
RULES = [
    ("Brute force SSH login", "wazuh", "Medium", 0.65),
    ("Impossible travel sign-in", "office365", "High", 0.3),
    ("Malware detected by EDR", "crowdstrike", "Critical", 0.05),
    ("Suspicious PowerShell execution", "wazuh", "High", 0.2),
    ("Port scan from external host", "graylog", "Low", 0.75),
    ("Privileged group membership change", "wazuh", "High", 0.1),
    ("Phishing link clicked", "office365", "Medium", 0.25),
    ("WAF SQL injection blocked", "waf", "Medium", 0.45),
    ("Ransomware note dropped", "sentinelone", "Critical", 0.0),
    ("DNS tunneling suspected", "graylog", "High", 0.5),
]
RULE_WEIGHTS = [18, 10, 3, 8, 14, 4, 9, 7, 1, 5]

# Override for Globex: a stricter High promise, so the policy editor has something to show.
POLICY = [
    PolicyRow("E2E_SLA_B", SlaEntity.ALERT, "High", 30, 240),
    PolicyRow("E2E_SLA_B", SlaEntity.CASE, "High", 30, 1440),
]


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow().replace(microsecond=0)


async def cleanup(s: AsyncSession) -> None:
    codes = list(CUSTOMERS)
    alert_ids = select(Alert.id).where(Alert.customer_code.in_(codes))
    case_ids = select(Case.id).where(Case.customer_code.in_(codes))
    await s.execute(delete(CaseAlertLink).where(CaseAlertLink.case_id.in_(case_ids)))
    for child in (CaseEvent, CaseComment, CaseTask):
        await s.execute(delete(child).where(child.case_id.in_(case_ids)))
    await s.execute(delete(Case).where(Case.customer_code.in_(codes)))
    await s.execute(delete(Comment).where(Comment.alert_id.in_(alert_ids)))
    await s.execute(delete(Alert).where(Alert.customer_code.in_(codes)))
    await s.execute(delete(SlaPolicy).where(SlaPolicy.customer_code.in_(codes)))
    for username in (ADMIN, SCOPED, *ANALYSTS):
        user = (await s.execute(select(User).where(User.username == username))).scalars().first()
        if user:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user.id))
            await s.delete(user)
    await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.customer_code.in_(codes)))
    await s.execute(delete(Customers).where(Customers.customer_code.in_(codes)))
    await s.commit()


def _minutes(rng: random.Random, median: float, spread: float = 0.9) -> datetime.timedelta:
    """A log-normal delay around ``median`` minutes: mostly near it, a long tail beyond."""
    return datetime.timedelta(minutes=max(1.0, rng.lognormvariate(0, spread) * median))


def _history(rng: random.Random, now: datetime.datetime):
    """One alert per yielded dict, oldest first, with its whole lifecycle decided."""
    customers = list(CUSTOMERS)
    for day in range(DAYS, 0, -1):
        for _ in range(rng.randint(3, 9)):
            title, source, severity, fp_share = rng.choices(RULES, weights=RULE_WEIGHTS)[0]
            customer = rng.choices(customers, weights=[5, 3, 2])[0]
            opened = now - datetime.timedelta(days=day) + datetime.timedelta(minutes=rng.randint(0, 24 * 60 - 1))
            yield {"title": title, "source": source, "severity": severity, "fp_share": fp_share, "customer": customer, "opened": opened}
    # Today: a few fresh ones, some about to breach their response clock.
    for minutes_ago in (5, 18, 42, 50, 55, 95, 170):
        title, source, severity, fp_share = rng.choices(RULES, weights=RULE_WEIGHTS)[0]
        yield {
            "title": title,
            "source": source,
            "severity": severity,
            "fp_share": fp_share,
            "customer": rng.choice(customers),
            "opened": now - datetime.timedelta(minutes=minutes_ago),
        }


def _who(rng: random.Random, customer: str) -> str:
    team = [*ANALYSTS, ADMIN] if customer != "E2E_SLA_A" else [SCOPED, SCOPED, *ANALYSTS]
    return rng.choice(team)


ACK_MEDIAN = {"Critical": 9, "High": 28, "Medium": 95, "Low": 240, "Informational": 600}
RESOLVE_MEDIAN = {"Critical": 150, "High": 300, "Medium": 900, "Low": 2400, "Informational": 4000}


async def seed(quiet: bool = False) -> dict:
    rng = random.Random(RANDOM_SEED)
    now = _now()
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        for role_id, name in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == role_id))).scalars().first():
                s.add(Role(id=role_id, name=name, description=name))
        await s.commit()
        await cleanup(s)

        for code, name in CUSTOMERS.items():
            s.add(Customers(customer_code=code, customer_name=name, contact_first_name="E2E", contact_last_name=code, logo_file=""))
        password = AuthHandler().get_password_hash(PASSWORD)
        s.add(User(username=ADMIN, password=password, email=f"{ADMIN}@e2e.example", role_id=1))
        for username in (SCOPED, *ANALYSTS):
            s.add(User(username=username, password=password, email=f"{username}@e2e.example", role_id=2))
        await s.commit()
        scoped_id = (await s.execute(select(User.id).where(User.username == SCOPED))).scalar_one()
        s.add(UserCustomerAccess(user_id=scoped_id, customer_code="E2E_SLA_A"))
        for row in POLICY:
            s.add(
                SlaPolicy(
                    customer_code=row.customer_code,
                    entity_type=row.entity.value,
                    severity=row.severity,
                    ack_minutes=row.ack_minutes,
                    resolve_minutes=row.resolve_minutes,
                    updated_by=ADMIN,
                ),
            )
        await s.commit()

        counts = {"alerts": 0, "open": 0, "cases": 0}
        ids = {"unacked_open_alert": {}, "case": {}}
        case_candidates = []
        for item in _history(rng, now):
            opened = item["opened"]
            targets = resolve_targets(SlaEntity.ALERT, item["severity"], item["customer"], POLICY)
            age = now - opened
            actor = _who(rng, item["customer"])

            ack = opened + _minutes(rng, ACK_MEDIAN[item["severity"]])
            acked = ack <= now and rng.random() < 0.97
            resolve = (ack if acked else opened) + _minutes(rng, RESOLVE_MEDIAN[item["severity"]], 1.1)
            resolved = acked and resolve <= now and rng.random() < (0.92 if age.days > 2 else 0.6)
            verdict = None
            if resolved and rng.random() < 0.8:
                verdict = "FALSE_POSITIVE" if rng.random() < item["fp_share"] else "TRUE_POSITIVE"

            status = "CLOSED" if resolved else ("IN_PROGRESS" if acked and rng.random() < 0.6 else "OPEN")
            assigned = actor if acked and rng.random() < 0.85 else None
            alert = Alert(
                alert_name=item["title"],
                alert_description=item["title"],
                status=status,
                alert_creation_time=opened,
                time_closed=resolve if resolved else None,
                customer_code=item["customer"],
                source=item["source"],
                severity=item["severity"],
                assigned_to=assigned,
                escalated=item["severity"] == "Critical" and rng.random() < 0.5,
                verdict=verdict,
                verdict_reason="RULE_TOO_SENSITIVE" if verdict == "FALSE_POSITIVE" else None,
                verdict_by=actor if verdict else None,
                verdict_at=resolve if verdict else None,
            )
            s.add(alert)
            await s.flush()
            s.add(
                AlertSlaTracking(
                    alert_id=alert.id,
                    severity=item["severity"],
                    opened_at=opened,
                    ack_due_at=targets.ack_due(opened),
                    resolve_due_at=targets.resolve_due(opened),
                    first_ack_at=ack if acked else None,
                    first_ack_by=actor if acked else None,
                    first_ack_action=rng.choice(["assigned", "status_changed", "commented"]) if acked else None,
                    first_assigned_at=ack if assigned else None,
                    resolved_at=resolve if resolved else None,
                    resolved_by=actor if resolved else None,
                    first_resolved_at=resolve if resolved else None,
                    reopen_count=1 if resolved and rng.random() < 0.04 else 0,
                    tracked=True,
                    updated_at=now,
                ),
            )
            counts["alerts"] += 1
            counts["open"] += status != "CLOSED"
            if status == "OPEN" and not acked:
                ids["unacked_open_alert"][item["customer"]] = alert.id
            if item["severity"] in ("Critical", "High") and verdict != "FALSE_POSITIVE" and rng.random() < 0.3:
                case_candidates.append((alert, ack if acked else opened, actor, resolved, resolve))
        await s.commit()

        for alert, created, actor, resolved, resolve in case_candidates[:14]:
            case_resolved = resolved and rng.random() < 0.6
            case_closed_at = resolve + _minutes(rng, 600) if case_resolved else None
            if case_closed_at and case_closed_at > now:
                case_resolved, case_closed_at = False, None
            case = Case(
                case_name=f"[INC] {alert.alert_name}",
                case_description=f"Investigation opened from alert #{alert.id}",
                case_creation_time=created,
                case_status="CLOSED" if case_resolved else "IN_PROGRESS",
                case_closed_time=case_closed_at,
                assigned_to=actor,
                customer_code=alert.customer_code,
            )
            s.add(case)
            await s.flush()
            s.add(CaseAlertLink(case_id=case.id, alert_id=alert.id))
            targets = resolve_targets(SlaEntity.CASE, alert.severity, alert.customer_code, POLICY)
            s.add(
                CaseSlaTracking(
                    case_id=case.id,
                    severity=alert.severity,
                    opened_at=created,
                    ack_due_at=targets.ack_due(created),
                    resolve_due_at=targets.resolve_due(created),
                    first_ack_at=created,
                    first_ack_by=actor,
                    first_ack_action="created",
                    first_assigned_at=created,
                    resolved_at=case_closed_at,
                    resolved_by=actor if case_closed_at else None,
                    first_resolved_at=case_closed_at,
                    tracked=True,
                    updated_at=now,
                ),
            )
            counts["cases"] += 1
            if not case_resolved:
                ids["case"].setdefault(case.customer_code, case.id)
        await s.commit()

    result = {
        "admin": ADMIN,
        "scoped_analyst": SCOPED,
        "analysts": ANALYSTS,
        "password": PASSWORD,
        "customers": CUSTOMERS,
        "scoped_customer": "E2E_SLA_A",
        "override_customer": "E2E_SLA_B",
        "rules": [rule[0] for rule in RULES],
        "ids": ids,
        **counts,
    }
    if not quiet:
        print(json.dumps(result))
    return result


async def _main(command: str) -> None:
    if command == "seed":
        await seed()
    elif command == "cleanup":
        async with AsyncSession(async_engine, expire_on_commit=False) as s:
            await cleanup(s)
    else:
        raise SystemExit("usage: soc_management_seed.py seed|cleanup")
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else "seed"))
