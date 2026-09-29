"""E2E: one imperfect stored row no longer fails the Customers and Users lists — NOT collected by pytest; run by hand.

Same disposable MySQL on 13306 as the other e2e scripts (see
customer_portal_overview_e2e.py for the setup), then:

    .venv/bin/python tests/e2e/list_responses_e2e.py

Real routers, real MySQL, real JWT. Rows the UI cannot create are inserted directly:
a customer without contact names (with customer meta missing its nullable columns)
and a user with a `.local` address. The lists must still answer 200 and include
them; creating the same things through the API must still be refused. Everything
inserted is removed at the end. Exits non-zero when a check fails.
"""

import asyncio
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import CustomersMeta  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.middleware.exception_handlers import validation_exception_handler  # noqa: E402
from app.middleware.exception_handlers import value_error_handler  # noqa: E402

ADMIN = "e2e_lists_admin"
INTERNAL = "e2e_lists_internal"
INTERNAL_EMAIL = "svc@corp.local"
LEGACY = "E2E_LEGACY"
PASSWORD = "E2ePassw0rd!x"

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def build_app():
    """The real routers and exception handlers, without the startup hooks."""
    from app.routers import auth
    from app.routers import customers

    app = FastAPI()
    for module in (auth, customers):
        app.include_router(module.router)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    return app


async def cleanup(s):
    for username in (ADMIN, INTERNAL):
        user = (await s.execute(select(User).where(User.username == username))).scalars().first()
        if user:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user.id))
            await s.delete(user)
    await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.customer_code == LEGACY))
    await s.execute(delete(CustomersMeta).where(CustomersMeta.customer_code == LEGACY))
    await s.execute(delete(Customers).where(Customers.customer_code.in_([LEGACY, "E2E_NEW"])))
    await s.commit()


async def seed():
    async with AsyncSession(async_engine) as s:
        for role_id, name in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == role_id))).scalars().first():
                s.add(Role(id=role_id, name=name, description=name))
        await s.commit()
        await cleanup(s)

        password = AuthHandler().get_password_hash(PASSWORD)
        s.add(User(username=ADMIN, password=password, email=f"{ADMIN}@e2e.example", role_id=1))
        # SQLModel table models do not validate, exactly like a row written by SQL.
        s.add(User(username=INTERNAL, password=password, email=INTERNAL_EMAIL, role_id=2))
        s.add(Customers(customer_code=LEGACY, customer_name="Legacy Customer", customer_type="MSSP", logo_file=""))
        await s.commit()
        s.add(
            CustomersMeta(
                customer_code=LEGACY,
                customer_name="Legacy Customer",
                customer_meta_graylog_index="idx",
                customer_meta_graylog_stream="stream",
                customer_meta_grafana_org_id="1",
                customer_meta_wazuh_group=LEGACY,
            ),
        )
        await s.commit()


async def main():
    await seed()
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        print("\n=== the lists answer, imperfect rows included ===")
        response = await client.get("/customers", headers=admin)
        legacy = next((c for c in response.json().get("customers", []) if c["customer_code"] == LEGACY), None)
        check("GET /customers: 200", response.status_code == 200, f"{response.status_code} {response.text[:160]}")
        check("the customer without contact names is listed", legacy is not None and legacy["contact_first_name"] is None, str(legacy))

        response = await client.get(f"/customers/{LEGACY}", headers=admin)
        check("GET /customers/{code}: 200", response.status_code == 200, f"{response.status_code} {response.text[:160]}")

        response = await client.get(f"/customers/{LEGACY}/meta", headers=admin)
        meta = response.json().get("customer_meta") or {}
        check(
            "GET /customers/{code}/meta: 200 with its null columns",
            response.status_code == 200 and meta.get("customer_meta_wazuh_api_port") is None,
            response.text[:160],
        )

        response = await client.get(f"/customers/{LEGACY}/full", headers=admin)
        check("GET /customers/{code}/full: 200", response.status_code == 200, f"{response.status_code} {response.text[:160]}")

        response = await client.get("/auth/users", headers=admin)
        emails = [u["email"] for u in response.json().get("users", [])]
        check("GET /auth/users: 200", response.status_code == 200, f"{response.status_code} {response.text[:160]}")
        check("the .local address is listed", INTERNAL_EMAIL in emails)

        internal_id = next((u["id"] for u in response.json().get("users", []) if u["username"] == INTERNAL), None)
        response = await client.get(f"/auth/users/{internal_id}", headers=admin)
        check(
            "GET /auth/users/{id}: 200",
            response.status_code == 200 and response.json()["user"]["email"] == INTERNAL_EMAIL,
            response.text[:160],
        )

        print("\n=== creating still enforces the rules ===")
        response = await client.post("/customers", headers=admin, json={"customer_code": "E2E_NEW", "customer_name": "New"})
        check("a customer without contact names is refused", response.status_code == 422, f"{response.status_code} {response.text[:160]}")

        response = await client.post(
            "/auth/register",
            headers=admin,
            json={"username": "e2e_lists_new", "password": "Str0ng!Passw0rd", "email": "new@corp.local", "role_id": 2},
        )
        check("a user with a .local address is refused", response.status_code == 422, f"{response.status_code} {response.text[:160]}")

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
        leftover = (await s.execute(select(User).where(User.username == "e2e_lists_new"))).scalars().first()
        if leftover:
            await s.delete(leftover)
            await s.commit()
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
