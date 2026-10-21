"""E2E for #1117 — several Microsoft 365 tenants under one customer.

NOT collected by pytest: it needs a live MySQL. Run by hand. It borrows a customer that already
has an unnamed Office365 integration; a database without one (the disposable 13306) gets a
seeded customer, removed again at the end.

    cd backend && PYTHONPATH=$PWD <venv>/bin/python tests/e2e/office365_multi_tenant_e2e.py

It connects through `app.db.db_session`, so it hits whatever database the repo `.env` (or the
MYSQL_* environment variables) points at, and it **writes**: it creates a second Office365
instance on a customer that already has one, updates it, and deletes it again. Point it
somewhere you are willing to have rows created in.

It drives the real `/integrations` routers over ASGI against the real database with a real
admin JWT, which is the point: the unit tests fake the session, so only this exercises the
SQL the instance-aware lookups actually emit (`IS NULL` for the unnamed instance especially,
which a fake session cannot get wrong).

It never calls `/office365/provision` — provisioning would create index sets, streams and
Grafana folders on the live stack. Everything here is settings-level.

The Office365 branch of `delete_integration` does reach out to the Wazuh manager to remove
the tenant's `<api_auth>` block. That is safe with the throwaway tenant GUID used here: the
GUID is not in ossec.conf, so the removal is a no-op and no manager restart is issued.

Leftovers: the script deletes what it created, and a `finally` block removes the rows
directly if an assertion aborted it first.
"""

import asyncio
import sys
import uuid

import httpx
from fastapi import APIRouter
from fastapi import FastAPI
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy import text

from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    CustomerIntegrations,
)
from app.integrations.models.customer_integration_settings import IntegrationAuthKeys
from app.integrations.models.customer_integration_settings import IntegrationConfig
from app.integrations.models.customer_integration_settings import IntegrationService
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)

INSTANCE = "e2e-tenant-b.onmicrosoft.com"
TENANT_ID = f"e2e-{uuid.uuid4()}"
# Used only when the database has no customer to borrow (a disposable one): created with an
# unnamed Office365 integration first, and removed with everything it holds at the end.
SEED_CUSTOMER = "E2E_O365"
SEED_TENANT_ID = f"e2e-{uuid.uuid4()}"

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))


def build_app():
    from app.integrations.routes import integration_settings_router

    api = APIRouter()
    api.include_router(integration_settings_router, prefix="/integrations")
    app = FastAPI()
    app.include_router(api)
    return app


async def pick_customer(conn):
    """A customer that already has an unnamed Office365 integration and the meta row creation needs."""
    row = (
        await conn.execute(
            text(
                "SELECT ci.customer_code, ci.customer_name FROM customer_integrations ci "
                "JOIN customersmeta cm ON cm.customer_code = ci.customer_code "
                "WHERE ci.integration_service_name = 'Office365' AND ci.instance_name IS NULL "
                # A seeded customer a crashed run left behind is seeded afresh, never borrowed.
                "AND ci.customer_code <> :seed LIMIT 1",
            ),
            {"seed": SEED_CUSTOMER},
        )
    ).first()
    return (row[0], row[1]) if row else (None, None)


async def admin_username(conn):
    """`encode_token` keys on the username, not the row id."""
    row = (await conn.execute(text("SELECT username FROM user WHERE role_id = 1 ORDER BY id LIMIT 1"))).first()
    return row[0] if row else None


async def instances_of(conn, customer_code):
    rows = (
        await conn.execute(
            text(
                "SELECT instance_name FROM customer_integrations "
                "WHERE customer_code = :c AND integration_service_name = 'Office365' ORDER BY id",
            ),
            {"c": customer_code},
        )
    ).all()
    return [r[0] for r in rows]


async def cleanup(customer_code, instance=INSTANCE):
    """Remove whatever this run created, whether or not the API delete got to run."""
    from sqlalchemy.ext.asyncio import AsyncSession

    named = CustomerIntegrations.instance_name.is_(None) if instance is None else CustomerIntegrations.instance_name == instance
    async with AsyncSession(async_engine) as session:
        ci_ids = (
            (
                await session.execute(
                    select(CustomerIntegrations.id).where(CustomerIntegrations.customer_code == customer_code, named),
                )
            )
            .scalars()
            .all()
        )
        if not ci_ids:
            return 0

        sub_rows = (
            await session.execute(
                select(IntegrationSubscription.id, IntegrationSubscription.integration_service_id).where(
                    IntegrationSubscription.customer_id.in_(ci_ids),
                ),
            )
        ).all()
        sub_ids = [r[0] for r in sub_rows]
        svc_ids = {r[1] for r in sub_rows}

        if sub_ids:
            await session.execute(sa_delete(IntegrationAuthKeys).where(IntegrationAuthKeys.subscription_id.in_(sub_ids)))
            await session.execute(sa_delete(IntegrationSubscription).where(IntegrationSubscription.id.in_(sub_ids)))
        if svc_ids:
            # Each creation makes its own service row; its config rows hold a key to it.
            await session.execute(sa_delete(IntegrationConfig).where(IntegrationConfig.integration_service_id.in_(svc_ids)))
            await session.execute(sa_delete(IntegrationService).where(IntegrationService.id.in_(svc_ids)))
        await session.execute(sa_delete(CustomerIntegrations).where(CustomerIntegrations.id.in_(ci_ids)))
        await session.commit()
        return len(ci_ids)


async def seed_customer():
    """A disposable customer with the meta row that creating an integration needs."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.db_setup import create_available_integrations
    from app.db.universal_models import Customers
    from app.db.universal_models import CustomersMeta

    await create_available_integrations(async_engine)
    await remove_seed_customer()
    async with AsyncSession(async_engine) as session:
        session.add(Customers(customer_code=SEED_CUSTOMER, customer_name="E2E Office365", customer_type="MSSP", logo_file=""))
        await session.commit()
        session.add(
            CustomersMeta(
                customer_code=SEED_CUSTOMER,
                customer_name="E2E Office365",
                customer_meta_graylog_index="",
                customer_meta_graylog_stream="",
                customer_meta_grafana_org_id="",
                customer_meta_wazuh_group="",
            ),
        )
        await session.commit()
    return SEED_CUSTOMER, "E2E Office365"


async def remove_seed_customer():
    """Everything the seeded customer holds, then the customer."""
    for instance in (INSTANCE, None):
        await cleanup(SEED_CUSTOMER, instance)
    async with async_engine.begin() as conn:
        for table in ("customer_integrations_meta", "custom_alert_creation_settings", "customersmeta"):
            await conn.execute(text(f"DELETE FROM {table} WHERE customer_code = :c"), {"c": SEED_CUSTOMER})
        await conn.execute(text("DELETE FROM customers WHERE customer_code = :c"), {"c": SEED_CUSTOMER})


async def build_index_set_for(customer_code):
    """Build the index set config a deploy would send to Graylog, without sending it."""
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

    from app.integrations.office365.services import provision

    async def one_shard():
        # The shard count is read from the indexer's nodes; this check is about the prefix only,
        # so it must not need a Wazuh indexer.
        return 1

    real, provision.output_shard_number_to_be_set_based_on_nodes = provision.output_shard_number_to_be_set_based_on_nodes, one_shard
    try:
        async with _AsyncSession(async_engine) as session:
            return await provision.build_index_set_config(customer_code, session)
    finally:
        provision.output_shard_number_to_be_set_based_on_nodes = real


def office365_payload(customer_code, customer_name, instance_name, tenant_id=None):
    payload = {
        "customer_code": customer_code,
        "customer_name": customer_name,
        "integration_name": "Office365",
        "integration_config": {"auth_type": "Wazuh", "config_key": "endpoint", "config_value": "not applicable"},
        "integration_auth_keys": [
            {"auth_key_name": "TENANT_ID", "auth_value": tenant_id or TENANT_ID},
            {"auth_key_name": "CLIENT_ID", "auth_value": "e2e-client"},
            {"auth_key_name": "CLIENT_SECRET", "auth_value": "e2e-secret"},
            {"auth_key_name": "API_TYPE", "auth_value": "commercial"},
        ],
    }
    if instance_name is not None:
        payload["instance_name"] = instance_name
    return payload


async def main():
    async with async_engine.connect() as conn:
        customer_code, customer_name = await pick_customer(conn)
        username = await admin_username(conn)

    seeded = not customer_code
    if not username:
        print("No admin user (role_id=1) in this database.")
        return 1

    app = build_app()
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://e2e", timeout=120) as client:
            H = {"Authorization": f"Bearer {await AuthHandler().encode_token(username)}"}

            if seeded:
                # No customer to borrow (a disposable database): make one, with its first tenant
                # unnamed, exactly as every integration configured before #1117 was.
                customer_code, customer_name = await seed_customer()
                r = await client.post(
                    "/integrations/create_integration",
                    json=office365_payload(customer_code, customer_name, None, SEED_TENANT_ID),
                    headers=H,
                )
                if r.status_code != 200:
                    print(f"Could not seed {customer_code}'s first Office365 tenant: {r.status_code} {r.text[:200]}")
                    return 1
            print(f"Customer under test: {customer_code} ({customer_name}){' (seeded)' if seeded else ''}; tenant GUID: {TENANT_ID}")

            print("\n=== 0) the existing unnamed instance is visible and reads as NULL ===")
            r = await client.get(f"/integrations/customer_integrations/{customer_code}", headers=H)
            o365 = [i for i in r.json().get("available_integrations", []) if i["integration_service_name"] == "Office365"]
            check("GET customer_integrations -> 200", r.status_code == 200, str(r.status_code))
            check("Office365 present with instance_name null", len(o365) == 1 and o365[0]["instance_name"] is None, str(o365))

            print("\n=== 1) a second tenant must be named ===")
            r = await client.post(
                "/integrations/create_integration",
                json=office365_payload(customer_code, customer_name, None),
                headers=H,
            )
            check("create without instance_name -> 400", r.status_code == 400, str(r.status_code))
            check("...and says to name it", "instance name" in r.text.lower(), r.text[:140])

            print("\n=== 2) a single-instance integration is unaffected ===")
            r = await client.post(
                "/integrations/create_integration",
                json={
                    **office365_payload(customer_code, customer_name, "whatever"),
                    "integration_name": "Mimecast",
                    # The real key names: auth-key validation runs before the instance check, so a
                    # wrong name would 400 for the wrong reason and prove nothing.
                    "integration_auth_keys": [
                        {"auth_key_name": name, "auth_value": "e2e"}
                        for name in ("APP_ID", "APP_KEY", "EMAIL_ADDRESS", "ACCESS_KEY", "SECRET_KEY")
                    ],
                },
                headers=H,
            )
            check("named instance on Mimecast -> 400", r.status_code == 400, str(r.status_code))
            check("...and says it is unsupported", "multiple instances" in r.text.lower(), r.text[:140])

            print("\n=== 3) a named second tenant is accepted ===")
            r = await client.post(
                "/integrations/create_integration",
                json=office365_payload(customer_code, customer_name, INSTANCE),
                headers=H,
            )
            check("create with instance_name -> 200", r.status_code == 200, f"{r.status_code} {r.text[:140]}")

            async with async_engine.connect() as conn:
                names = await instances_of(conn, customer_code)
            check("both instances now exist in the DB", sorted(map(str, names)) == sorted([str(None), INSTANCE]), str(names))

            r = await client.get(f"/integrations/customer_integrations/{customer_code}", headers=H)
            o365 = [i for i in r.json().get("available_integrations", []) if i["integration_service_name"] == "Office365"]
            check("API lists both Office365 instances", len(o365) == 2, str([i["instance_name"] for i in o365]))

            print("\n=== 4) the same name cannot be reused ===")
            r = await client.post(
                "/integrations/create_integration",
                json=office365_payload(customer_code, customer_name, INSTANCE),
                headers=H,
            )
            check("duplicate instance_name -> 400", r.status_code == 400, str(r.status_code))

            print("\n=== 5) an ambiguous request is refused rather than guessed ===")
            r = await client.put(
                f"/integrations/update_integration/{customer_code}",
                json={"integration_name": "Office365", "integration_auth_keys": [{"auth_key_name": "CLIENT_ID", "auth_value": "x"}]},
                headers=H,
            )
            check("update without instance_name -> 400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")

            r = await client.request(
                "DELETE",
                "/integrations/delete_integration",
                json={"customer_code": customer_code, "integration_name": "Office365"},
                headers=H,
            )
            check("delete without instance_name -> 400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")

            print("\n=== 6) naming the instance addresses exactly that one ===")
            r = await client.put(
                f"/integrations/update_integration/{customer_code}",
                json={
                    "integration_name": "Office365",
                    "instance_name": INSTANCE,
                    "integration_auth_keys": [{"auth_key_name": "CLIENT_ID", "auth_value": "e2e-client-updated"}],
                },
                headers=H,
            )
            check("update with instance_name -> 200", r.status_code == 200, f"{r.status_code} {r.text[:140]}")

            async with async_engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT ak.auth_value FROM integration_auth_keys ak "
                            "JOIN integration_subscriptions s ON s.id = ak.subscription_id "
                            "JOIN customer_integrations ci ON ci.id = s.customer_id "
                            "WHERE ci.customer_code = :c AND ci.instance_name = :i AND ak.auth_key_name = 'CLIENT_ID'",
                        ),
                        {"c": customer_code, "i": INSTANCE},
                    )
                ).first()
            check("the named instance's key changed", row is not None and row[0] == "e2e-client-updated", str(row))

            async with async_engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT ak.auth_value FROM integration_auth_keys ak "
                            "JOIN integration_subscriptions s ON s.id = ak.subscription_id "
                            "JOIN customer_integrations ci ON ci.id = s.customer_id "
                            "WHERE ci.customer_code = :c AND ci.instance_name IS NULL AND ak.auth_key_name = 'CLIENT_ID'",
                        ),
                        {"c": customer_code},
                    )
                ).first()
            check("the unnamed instance's key did NOT change", row is None or row[0] != "e2e-client-updated", str(row))

            print("\n=== 7) tenant GUID resolves to the customer without the legacy column ===")
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.integrations.office365.services.tenant_lookup import (
                resolve_customer_code_from_office365_tenant,
            )

            async with AsyncSession(async_engine) as session:
                resolved = await resolve_customer_code_from_office365_tenant(TENANT_ID, session)
            check("second tenant GUID -> owning customer", resolved == customer_code, str(resolved))

            print("\n=== 7b) deploying the second tenant reuses the customer's index set ===")
            # The reported failure: a per-tenant index prefix `office365-<code>-<tenant>` is
            # rejected by Graylog because it extends the first tenant's `office365-<code>`.
            index_set = await build_index_set_for(customer_code)
            check(
                "index prefix depends on the customer only",
                index_set.index_prefix == f"office365-{customer_code.lower()}",
                index_set.index_prefix,
            )

            print("\n=== 8) deleting the named instance leaves the unnamed one alone ===")
            r = await client.request(
                "DELETE",
                "/integrations/delete_integration",
                json={"customer_code": customer_code, "integration_name": "Office365", "instance_name": INSTANCE},
                headers=H,
            )
            check("delete with instance_name -> 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

            async with async_engine.connect() as conn:
                names = await instances_of(conn, customer_code)
            check("only the unnamed instance remains", names == [None], str(names))

    finally:
        if customer_code:
            removed = await cleanup(customer_code)
            if removed:
                print(f"\n(cleanup removed {removed} leftover instance row(s))")
        if seeded:
            await remove_seed_customer()
        await async_engine.dispose()

    print("\n" + "=" * 60)
    failed = [n for n, ok, _ in results if not ok]
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    for n in failed:
        print(f"  FAILED: {n}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
