"""E2E for #1258 (event search in the Customer Portal) — NOT collected by pytest (needs a
live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    .venv/bin/python tests/e2e/event_search_e2e.py

Real routers, real MySQL, a real portal login, real event sources. The Wazuh indexer is
replaced by a recorder (no indexer here). The portal's saved queries, export and columns
live in the browser; what the server must guarantee is that every route they lean on keeps
to the user's own customer:

  A) the portal user lists their customer's sources and runs a search, its next page, the
     field list and one event;
  B) another customer: 403 on sources, search, next page, fields and event, and the
     indexer is never asked;
  C) the next-page token is the search's own: a token for another customer, another source
     or a bare scroll id is refused before the indexer is asked (it was continued as given
     before #1258);
  D) a disabled source: refused, its next page too.

Exits non-zero when a check fails.
"""

import asyncio
import os
import sys
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.siem.services.events as event_services  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import EventSources  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def build_app():
    """The real auth and SIEM routers, without the startup hooks."""
    from app.routers import auth
    from app.routers import siem

    app = FastAPI()
    for module in (auth, siem):
        app.include_router(module.router)
    return app


class FakeIndexer:
    """What CoPilot asks the indexer, with one scroll context per search, like the real one."""

    def __init__(self):
        self.asked: list[tuple] = []
        self.contexts = 0

    def client(self):
        indexer = self

        class Client:
            async def search(self, index, body, size, scroll):
                indexer.asked.append(("search", index))
                indexer.contexts += 1
                return {"_scroll_id": f"ctx-{indexer.contexts}", "hits": {"total": {"value": 3}, "hits": [_hit(index, 0)]}}

            async def scroll(self, scroll_id, scroll):
                indexer.asked.append(("scroll", scroll_id))
                return {"_scroll_id": scroll_id, "hits": {"total": {"value": 3}, "hits": [_hit(scroll_id, 1)]}}

            async def clear_scroll(self, scroll_id):
                pass

            async def field_caps(self, index, **kwargs):
                indexer.asked.append(("field_caps", index))
                return {"fields": {"timestamp": {"date": {"type": "date"}}, "agent_name": {"keyword": {"type": "keyword"}}}}

            async def get(self, index, id):
                indexer.asked.append(("get", index))
                return {"_id": id, "_index": index, "_source": {"agent_name": "web-01"}}

            async def close(self):
                pass

        async def create(_name):
            return Client()

        return create


def _hit(where, n):
    return {"_id": f"e{n}", "_index": "wazuh-a-1", "_source": {"from": where, "n": n}}


async def seed_sources():
    async with AsyncSession(async_engine) as s:
        for code, pattern in ((CUST_A, "wazuh-a-*"), (CUST_B, "wazuh-b-*")):
            s.add(EventSources(customer_code=code, name="Wazuh", index_pattern=pattern, event_type="EDR"))
            s.add(EventSources(customer_code=code, name="Office", index_pattern=f"o365-{code.lower()}-*", event_type="Cloud"))
        s.add(EventSources(customer_code=CUST_A, name="Old", index_pattern="old-a-*", event_type="EDR", enabled=False))
        await s.commit()


async def main():
    await seed()
    await seed_sources()
    indexer = FakeIndexer()
    secret = AuthHandler().secret

    with patch.object(event_services, "create_wazuh_indexer_client_async", indexer.client()):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
            login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
            portal = {"Authorization": f"Bearer {login.json()['access_token']}"}
            admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

            def search(code, source="Wazuh", headers=portal, **params):
                return client.get(f"/siem/events/{code}/{source}", params={"timerange": "24h", **params}, headers=headers)

            print("\n=== A) the portal user searches their own customer ===")
            response = await client.get(f"/siem/event_sources/{CUST_A}", headers=portal)
            check("sources: 200", response.status_code == 200, response.text[:120])
            check(
                "sources: their customer's, the disabled one included (the portal hides it)",
                sorted(s["name"] for s in response.json()["event_sources"]) == ["Office", "Old", "Wazuh"],
            )
            first = await search(CUST_A, query="rule_level:>=10")
            check("search: 200", first.status_code == 200, first.text[:120])
            check("search: on the source's own indices", indexer.asked[-1] == ("search", "wazuh-a-*"), str(indexer.asked[-1:]))
            token = first.json()["scroll_id"]
            check("search: the next page is a signed token, not the indexer's scroll id", token and token != "ctx-1", str(token))
            second = await search(CUST_A, scroll_id=token)
            check("next page: 200", second.status_code == 200, second.text[:120])
            check("next page: continues that search", indexer.asked[-1] == ("scroll", "ctx-1"), str(indexer.asked[-1:]))
            check("next page: hands out a token of its own", second.json()["scroll_id"] not in (None, "ctx-1"))
            third = await search(CUST_A, scroll_id=second.json()["scroll_id"])
            check("the page after: 200 too", third.status_code == 200, third.text[:120])
            fields = await client.get(f"/siem/events/{CUST_A}/Wazuh/fields", headers=portal)
            check("fields: 200", fields.status_code == 200 and fields.json()["total"] == 2, fields.text[:120])
            document = await client.get(
                f"/siem/events/{CUST_A}/Wazuh/document",
                params={"index_name": "wazuh-a-1", "event_id": "e0"},
                headers=portal,
            )
            check("one event: 200", document.status_code == 200, document.text[:120])

            print("\n=== B) another customer: 403 everywhere, the indexer never asked ===")
            b_first = await search(CUST_B, headers=admin)
            b_token = b_first.json()["scroll_id"]
            indexer.asked.clear()
            for name, request in (
                ("sources", client.get(f"/siem/event_sources/{CUST_B}", headers=portal)),
                ("search", search(CUST_B)),
                ("next page, with B's own token", search(CUST_B, scroll_id=b_token)),
                ("fields", client.get(f"/siem/events/{CUST_B}/Wazuh/fields", headers=portal)),
                (
                    "one event",
                    client.get(
                        f"/siem/events/{CUST_B}/Wazuh/document",
                        params={"index_name": "wazuh-b-1", "event_id": "e0"},
                        headers=portal,
                    ),
                ),
            ):
                response = await request
                check(f"{name}: 403", response.status_code == 403, f"{response.status_code} {response.text[:80]}")
            check("the indexer was never asked", indexer.asked == [], str(indexer.asked))

            print("\n=== C) the next-page token belongs to its search ===")
            a_office = (await search(CUST_A, source="Office")).json()["scroll_id"]
            indexer.asked.clear()
            for name, source, presented in (
                ("B's token, on A's path", "Wazuh", b_token),
                ("A's Office token, on A's Wazuh", "Wazuh", a_office),
                ("a bare scroll id (B's context)", "Wazuh", b_token.rpartition(".")[0]),
                ("a token re-signed with another key", "Wazuh", f"ctx-1.{'0' * 64}"),
            ):
                response = await search(CUST_A, source=source, scroll_id=presented)
                check(f"{name}: 400", response.status_code == 400, f"{response.status_code} {response.text[:80]}")
            check("the indexer never scrolled them", indexer.asked == [], str(indexer.asked))
            check("the refusal says what to do", "run the search again" in response.text, response.text[:120])

            print("\n=== D) a disabled source ===")
            check("search: 400", (await search(CUST_A, source="Old")).status_code == 400)
            from app.siem.utils.scroll_token import sign_scroll

            response = await search(CUST_A, source="Old", scroll_id=sign_scroll("ctx-1", CUST_A, "Old", secret))
            check("next page: 400, even with a valid token", response.status_code == 400, response.text[:80])
            check("the indexer was never asked", indexer.asked == [], str(indexer.asked))

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
