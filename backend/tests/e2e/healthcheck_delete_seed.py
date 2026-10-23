"""Seed for the browser e2e of #1291 (frontend/e2e/healthcheck-delete.spec.ts) on the disposable MySQL
on 13306 — never a real one. Idempotent: every run starts from the same rows.

    cd backend && PYTHONPATH=$PWD .venv/bin/python tests/e2e/healthcheck_delete_seed.py

One customer, ``E2E_HDW``, with agents the healthcheck sees at a 30-day threshold as: gone from both
tools (deletable), gone from Wazuh but still seen by Velociraptor (kept unless included), seen
recently, and never enrolled in Velociraptor (deletable); plus an admin, ``e2e_hd_admin``.
"""

import asyncio
import os
from datetime import timedelta

for key, value in {
    "MYSQL_URL": "127.0.0.1:13306",
    "MYSQL_USER": "copilot",
    "MYSQL_PASSWORD": "e2epass",
    "MYSQL_ROOT_PASSWORD": "e2eroot",
    "JWT_SECRET": "e2e-test-secret-not-the-default",
}.items():
    os.environ.setdefault(key, value)

from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import AgentVulnerabilities  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.time_utils import now_utc  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402

CUSTOMER = "E2E_HDW"
ADMIN = "e2e_hd_admin"
PASSWORD = "E2ePlaywr1ght!hd"
PREFIX = "e2ehdw-"

#: agent id suffix → (days since Wazuh saw it, days since Velociraptor did; None = no client)
AGENTS = {
    "gone-1": (40, 41),
    "gone-2": (90, 90),
    "gone-3": (35, 36),
    "novelo": (50, None),
    "velo-alive": (45, 0.05),
    "fresh": (0.05, 0.05),
}


async def seed(dispose: bool = True):
    """Every run starts from the same rows. ``dispose`` closes the engine's pool: a script must, a
    running server must not."""
    now = to_naive_utc(now_utc())
    async with AsyncSession(async_engine) as s:
        for rid, name in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user"), (5, "responder")]:
            if not (await s.execute(select(Role).where(Role.id == rid))).scalars().first():
                s.add(Role(id=rid, name=name, description=name))
        await s.execute(delete(AuditLog).where(AuditLog.entity_id.like(f"{PREFIX}%")))
        await s.execute(delete(AgentVulnerabilities).where(AgentVulnerabilities.customer_code == CUSTOMER))
        await s.execute(delete(Agents).where(Agents.customer_code == CUSTOMER))
        await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.customer_code == CUSTOMER))
        admin = (await s.execute(select(User).where(User.username == ADMIN))).scalars().first()
        if admin:
            await s.delete(admin)
        await s.commit()

        if not (await s.execute(select(Customers).where(Customers.customer_code == CUSTOMER))).scalars().first():
            s.add(
                Customers(
                    customer_code=CUSTOMER,
                    customer_name="E2E Healthcheck",
                    contact_first_name="E2E",
                    contact_last_name="Tester",
                    phone="000",
                    address_line1="a",
                    address_line2="b",
                    city="c",
                    state="d",
                    postal_code="1",
                    country="IT",
                    customer_type="MSSP",
                    logo_file="",
                ),
            )
        s.add(User(username=ADMIN, password=AuthHandler().get_password_hash(PASSWORD), email=f"{ADMIN}@e2e.example", role_id=1))
        await s.commit()

        for index, (suffix, (wazuh_days, velo_days)) in enumerate(AGENTS.items()):
            agent_id = f"{PREFIX}{suffix}"
            s.add(
                Agents(
                    agent_id=agent_id,
                    ip_address=f"10.9.0.{index + 1}",
                    os="Windows",
                    hostname=f"HD-{suffix.upper()}",
                    label=suffix,
                    critical_asset=False,
                    customer_code=CUSTOMER,
                    quarantined=False,
                    velociraptor_id=f"C.{index + 1:016x}" if velo_days is not None else None,
                    velociraptor_org="root" if velo_days is not None else None,
                    wazuh_last_seen=now - timedelta(days=wazuh_days),
                    velociraptor_last_seen=now - timedelta(days=velo_days) if velo_days is not None else None,
                    wazuh_agent_version="v4.9.0",
                    velociraptor_agent_version="0.7.4" if velo_days is not None else None,
                ),
            )
        await s.commit()
    if dispose:
        await async_engine.dispose()
    print(f"seed: {CUSTOMER} with {len(AGENTS)} agents, admin {ADMIN}")


if __name__ == "__main__":
    asyncio.run(seed())
