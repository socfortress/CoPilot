"""E2E for #1245 (`GET /incidents/db_operations/alerts/filter`) — NOT collected by pytest
(needs a live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    .venv/bin/python tests/e2e/alert_filters_e2e.py

Real routers, real MySQL, a real portal login, against the seeded alerts (each with its
own status, source, day and tags — see ALERT_ROWS_A in portal_overview_seed.py):

  A) every criterion on its own, and combined (AND; tags match any of them);
  B) the creation-date range: inclusive on both ends, open on either side, an aware
     time read in its own offset, a reversed range refused with a 422;
  C) the portal user never sees customer B, even when asking for it by code;
  D) a tag-restricted analyst: the page and `total_filtered` agree (the count used to
     ignore tag RBAC and count every alert of the customer).

Every expectation is computed from the seed's own rows, not written out by hand.
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
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.models.users import UserTagAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import TagAccessSettings  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import TAG_PHISHING  # noqa: E402
from tests.e2e.portal_overview_seed import TAG_VIP  # noqa: E402
from tests.e2e.portal_overview_seed import alert_rows  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

TAG_ANALYST = "e2e_ov_tag_analyst"

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def expected(rows, title=None, status=None, source=None, asset=None, tags=None, day_from=None, day_to=None):
    """The names of the seeded rows a query must return, newest first like the API."""
    return [
        row["name"]
        for row in reversed(rows)
        if (title is None or title.lower() in row["name"].lower())
        and (status is None or row["status"] == status)
        and (source is None or row["source"] == source)
        and (asset is None or asset in row["assets"])
        and (tags is None or set(tags) & set(row["tags"]))
        and (day_from is None or row["day"] >= day_from)
        and (day_to is None or row["day"] <= day_to)
    ]


def day_start(day: str) -> str:
    return f"{day}T00:00:00Z"


def day_end(day: str) -> str:
    return f"{day}T23:59:59Z"


async def add_tag_analyst():
    """An analyst of A who may see only VIP-tagged alerts, with tag RBAC switched on."""
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        settings = (await s.execute(select(TagAccessSettings))).scalars().first()
        previous = (settings.enabled, settings.untagged_alert_behavior) if settings else None
        if not settings:
            settings = TagAccessSettings()
            s.add(settings)
        settings.enabled, settings.untagged_alert_behavior = True, "admin_only"
        analyst = User(
            username=TAG_ANALYST,
            password=AuthHandler().get_password_hash(PASSWORD),
            email=f"{TAG_ANALYST}@e2e.example",
            role_id=2,
        )
        s.add(analyst)
        await s.commit()
        vip = (await s.execute(select(AlertTag).where(AlertTag.tag == TAG_VIP))).scalars().one()
        s.add(UserCustomerAccess(user_id=analyst.id, customer_code=CUST_A))
        s.add(UserTagAccess(user_id=analyst.id, tag_id=vip.id))
        await s.commit()
        return settings.id, previous


async def remove_tag_analyst(settings_id, previous):
    async with AsyncSession(async_engine) as s:
        analyst = (await s.execute(select(User).where(User.username == TAG_ANALYST))).scalars().first()
        if analyst:
            await s.execute(delete(UserTagAccess).where(UserTagAccess.user_id == analyst.id))
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == analyst.id))
            await s.delete(analyst)
        settings = await s.get(TagAccessSettings, settings_id)
        if previous is None:
            await s.delete(settings)
        else:
            settings.enabled, settings.untagged_alert_behavior = previous
        await s.commit()


async def main():
    await seed()
    rows_a = alert_rows("A")
    days = sorted({row["day"] for row in rows_a})

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
        portal = {"Authorization": f"Bearer {login.json()['access_token']}"}

        async def listed(headers=portal, **params):
            response = await client.get("/incidents/db_operations/alerts/filter", headers=headers, params={"page_size": 100, **params})
            body = response.json()
            return response.status_code, [alert["alert_name"] for alert in body.get("alerts", [])], body.get("total_filtered"), body

        async def expect(name, want, headers=portal, **params):
            status, names, total, body = await listed(headers, **params)
            check(
                name,
                status == 200 and names == want and total == len(want),
                f"got {names} / total {total}; want {want}" if status == 200 else body,
            )

        print("\n=== A) every criterion, alone and combined ===")
        await expect("no criteria: every alert of A, newest first", expected(rows_a))
        await expect("title, case-insensitive substring", expected(rows_a, title="ALERT 1"), alert_title="ALERT 1")
        await expect("status", expected(rows_a, status="OPEN"), status="OPEN")
        await expect("source", expected(rows_a, source="office365"), source="office365")
        await expect("asset", expected(rows_a, asset="host-a2"), asset_name="host-a2")
        await expect("one tag", expected(rows_a, tags=[TAG_VIP]), tags=[TAG_VIP])
        await expect("several tags match any of them", expected(rows_a, tags=[TAG_VIP, TAG_PHISHING]), tags=[TAG_VIP, TAG_PHISHING])
        await expect(
            "status AND source AND tag",
            expected(rows_a, status="OPEN", source="office365", tags=[TAG_VIP]),
            status="OPEN",
            source="office365",
            tags=[TAG_VIP],
        )
        await expect("criteria nothing satisfies together: empty, total 0", [], status="CLOSED", source="office365")

        print("\n=== B) the creation-date range ===")
        first, second, middle, last = days[0], days[1], days[len(days) // 2], days[-1]
        await expect(
            "inclusive on both ends",
            expected(rows_a, day_from=middle, day_to=last),
            date_from=day_start(middle),
            date_to=day_end(last),
        )
        await expect("one day", expected(rows_a, day_from=last, day_to=last), date_from=day_start(last), date_to=day_end(last))
        await expect("open on the left", expected(rows_a, day_to=middle), date_to=day_end(middle))
        await expect("open on the right", expected(rows_a, day_from=middle), date_from=day_start(middle))
        await expect(
            "with the other criteria",
            expected(rows_a, status="OPEN", day_from=second),
            status="OPEN",
            date_from=day_start(second),
        )
        # Midnight in Rome is 22:00 UTC the day before: still covers the whole UTC day.
        rome_midnight = f"{last}T00:00:00+02:00"
        await expect("an aware time is read in its own offset", expected(rows_a, day_from=last), date_from=rome_midnight)
        status, _, _, body = await listed(date_from=day_start(last), date_to=day_end(first))
        check("a reversed range: 422", status == 422, str(body)[:200])

        print("\n=== C) the portal user stays on their customer ===")
        await expect("asking for B by code returns nothing", [], customer_codes=[CUST_B])
        await expect("asking for A and B returns A only", expected(rows_a), customer_codes=[CUST_A, CUST_B])
        await expect(
            "a source only B has an alert of does not leak B",
            expected(rows_a, source="office365", tags=[TAG_PHISHING]),
            source="office365",
            tags=[TAG_PHISHING],
        )

        print("\n=== D) a tag-restricted analyst: page and count agree ===")
        settings_id, previous = await add_tag_analyst()
        try:
            analyst = {"Authorization": f"Bearer {await AuthHandler().encode_token(TAG_ANALYST)}"}
            vip_only = expected(rows_a, tags=[TAG_VIP])
            await expect("only the VIP-tagged alerts, and a count of exactly those", vip_only, headers=analyst)
            await expect(
                "filtered by status, still within the tags",
                expected(rows_a, tags=[TAG_VIP], status="OPEN"),
                headers=analyst,
                status="OPEN",
            )
            await expect(
                "a tag on visible and hidden alerts returns the visible ones only",
                [name for name in expected(rows_a, tags=[TAG_PHISHING]) if name in vip_only],
                headers=analyst,
                tags=[TAG_PHISHING],
            )
        finally:
            await remove_tag_analyst(settings_id, previous)

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
