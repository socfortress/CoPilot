"""E2E for #1243 (`GET /customer_portal/me`) — NOT collected by pytest (needs a live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    .venv/bin/python tests/e2e/customer_portal_me_e2e.py

Real routers, real MySQL, a real portal login:

  A) the portal user gets their customers with names, not just codes;
  B) the list is read live: after an admin assigns a second customer, the *same* token
     (whose customer_codes claim still says one) gets both at the next call;
  C) the route is for portal users only (an admin token gets 403, no token 401).

Exits non-zero when a check fails.
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
import jose.jwt  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import CUSTOMER_NAMES  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def main():
    portal_user_id = (await seed())["portal_user_id"]
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
        token = login.json()["access_token"]
        portal = {"Authorization": f"Bearer {token}"}

        async def me(headers):
            return await client.get("/customer_portal/me", headers=headers)

        print("\n=== A) customers come with their names ===")
        response = await me(portal)
        body = response.json()
        check("200 for the portal user", response.status_code == 200, response.text[:200])
        check("username and role", (body.get("username"), body.get("role")) == (PORTAL_USER, "customer_user"), str(body)[:200])
        check(
            "the assigned customer, named",
            # Not an administrator of its users unless the SOC says so (#1296).
            body.get("customers")
            == [{"customer_code": CUST_A, "customer_name": CUSTOMER_NAMES[CUST_A], "is_customer_admin": False, "read_only": False}],
            str(body.get("customers")),
        )

        print("\n=== B) read live, not from the token ===")
        await client.post(f"/auth/users/{portal_user_id}/customers", headers=admin, json=[CUST_A, CUST_B])
        claim = jose.jwt.get_unverified_claims(token).get("customer_codes")
        body = (await me(portal)).json()
        check("the token still claims one customer", claim == [CUST_A], str(claim))
        check(
            "the same token now gets both, sorted by name",
            [c["customer_code"] for c in body.get("customers", [])] == [CUST_A, CUST_B],
            str(body.get("customers")),
        )
        await client.post(f"/auth/users/{portal_user_id}/customers", headers=admin, json=[CUST_A])

        print("\n=== C) portal users only ===")
        check("an admin token gets 403", (await me(admin)).status_code == 403)
        check("no token gets 401", (await me({})).status_code == 401)

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
