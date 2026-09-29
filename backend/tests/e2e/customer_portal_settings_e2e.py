"""E2E for #1188 (portal settings/branding cleanup) — NOT collected by pytest (needs a live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    .venv/bin/python tests/e2e/customer_portal_settings_e2e.py

Real routers, real MySQL, real JWTs, the real exception handlers:

  A) POST /customer_portal/settings still replaces everything; PATCH changes only the
     fields sent and resets only what ``reset`` names;
  B) a bad field is the standard 422 naming it (no longer an ad-hoc 400), on POST,
     PATCH and the per-customer branding PUT;
  C) a service's 404 reaches the client as a 404, never a 500 carrying the error text;
  D) timestamps are written as UTC wall-clock time, as before;
  E) case filter options stay scoped to the caller's customers after moving into a service.

The global settings are restored at the end. Exits non-zero when a check fails.
"""

import asyncio
import os
import sys
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalSettings  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.middleware.exception_handlers import validation_exception_handler  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

PNG = "iVBORw0KGgo="
GIF = "R0lGODlh"

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def stored_updated_at() -> datetime:
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(CustomerPortalSettings.updated_at).limit(1))).scalar_one()


async def main():
    await seed()
    auth = AuthHandler()
    admin = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
    portal = {"Authorization": f"Bearer {await auth.encode_token(PORTAL_USER)}"}

    app = build_app()
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    async with AsyncSession(async_engine) as s:
        s.add(
            Case(case_name="e2e B", case_description="e2e B", case_status="IN_PROGRESS", customer_code=CUST_B, assigned_to="e2e-b-analyst"),
        )
        await s.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e") as client:

        async def stored():
            return (await client.get("/customer_portal/settings/global", headers=admin)).json()["settings"]

        original = await stored()

        print("\n=== A) POST replaces, PATCH changes only what it is sent ===")
        full = {"title": "E2E Portal", "logo_base64": PNG, "logo_mime_type": "image/png", "brand_color": "#112233"}
        response = await client.post("/customer_portal/settings", headers=admin, json=full)
        check("POST saves every field", response.status_code == 200 and {k: (await stored())[k] for k in full} == full, response.text[:200])

        response = await client.patch("/customer_portal/settings", headers=admin, json={"title": "Renamed"})
        now = await stored()
        check(
            "PATCH title keeps the logo and colour",
            response.status_code == 200 and (now["title"], now["logo_base64"], now["brand_color"]) == ("Renamed", PNG, "#112233"),
            str(now)[:200],
        )

        await client.patch("/customer_portal/settings", headers=admin, json={"logo_base64": GIF, "logo_mime_type": "image/gif"})
        now = await stored()
        check(
            "PATCH replaces the logo with its MIME type",
            (now["logo_base64"], now["logo_mime_type"], now["title"]) == (GIF, "image/gif", "Renamed"),
        )

        await client.patch("/customer_portal/settings", headers=admin, json={"reset": ["logo"]})
        now = await stored()
        public = (await client.get("/customer_portal/settings")).json()["settings"]
        check("PATCH reset removes only the logo", (now["logo_base64"], now["logo_mime_type"], now["title"]) == (None, None, "Renamed"))
        check("the public settings follow", public["logo_url"] is None and public["title"] == "Renamed", str(public))

        response = await client.post("/customer_portal/settings", headers=admin, json={"title": "Only title"})
        now = await stored()
        check("POST still resets what it omits", now["brand_color"] is None and now["title"] == "Only title", str(now)[:200])

        response = await client.patch("/customer_portal/settings", headers=portal, json={"title": "Hijack"})
        check("PATCH is admin-only", response.status_code in (401, 403), str(response.status_code))

        print("\n=== B) a bad field is the standard 422 naming it ===")
        for method, url, body in (
            ("POST", "/customer_portal/settings", {"brand_color": "red"}),
            ("PATCH", "/customer_portal/settings", {"brand_color": "red"}),
            ("PUT", f"/customer_portal/branding/{CUST_A}", {"enabled": True, "brand_color": "red"}),
        ):
            response = await client.request(method, url, headers=admin, json=body)
            message = response.json().get("message")
            check(
                f"{method} {url.split('/customer_portal')[1]}: 422",
                response.status_code == 422 and message == "brand_color: Expected a hex color like #RGB or #RRGGBB",
                f"{response.status_code} {message}",
            )
        response = await client.patch("/customer_portal/settings", headers=admin, json={})
        check(
            "an empty PATCH says so",
            response.status_code == 422 and "Nothing to update" in response.json()["message"],
            response.text[:200],
        )

        print("\n=== C) a service's 404 stays a 404 ===")
        for method, url, body in (
            ("PUT", "/customer_portal/branding/E2E_NOPE", {"enabled": True, "title": "x"}),
            ("PUT", "/customer_portal/ai_reports/settings/E2E_NOPE", {"enabled": True}),
        ):
            response = await client.request(method, url, headers=admin, json=body)
            check(
                f"{url}: 404",
                response.status_code == 404 and response.json()["message"] == "Customer E2E_NOPE not found",
                response.text[:200],
            )

        print("\n=== D) timestamps are UTC wall-clock time ===")
        await client.patch("/customer_portal/settings", headers=admin, json={"title": "Timestamp"})
        written = await stored_updated_at()
        drift = abs(written - datetime.utcnow())
        check(
            "updated_at is stored naive and in UTC",
            written.tzinfo is None and drift < timedelta(minutes=1),
            f"{written} (drift {drift})",
        )

        print("\n=== E) case filter options stay scoped ===")
        mine = (await client.get("/incidents/db_operations/cases/filter-options", headers=portal)).json()
        everyone = (await client.get("/incidents/db_operations/cases/filter-options", headers=admin)).json()
        check(
            "portal user: own customer's statuses only",
            "IN_PROGRESS" not in mine["statuses"] and "OPEN" in mine["statuses"],
            str(mine["statuses"]),
        )
        check("portal user: own customer's assignees only", "e2e-b-analyst" not in mine["assigned_to"], str(mine["assigned_to"]))
        check("admin: every customer", "IN_PROGRESS" in everyone["statuses"] and "e2e-b-analyst" in everyone["assigned_to"])

        restore = {k: original[k] for k in ("title", "logo_base64", "logo_mime_type", "brand_color")}
        await client.post("/customer_portal/settings", headers=admin, json=restore)

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
