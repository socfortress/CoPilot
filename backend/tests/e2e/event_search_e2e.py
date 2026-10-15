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
  D) a disabled source: refused, its next page too;
  E) what the user saves is on the server: a second login (another device) finds it, a
     name saved again (whatever its case) updates it, an absolute range keeps its instant;
  F) recent searches: once each whatever the page size, newest first, the last ten;
  G) columns per source, found from the other device, and back to the source's layout;
  H) at most 50 saved queries per customer: the next one is refused, not dropped;
  I) another user sees none of it and cannot delete it, another customer is a 403;
  J) deleting the user and the customer takes their rows with them;
  K) column templates: named per source, found from the other device, updated by name,
     at most 20 per source, never someone else's.

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
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.siem.services.events as event_services  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import EventSources  # noqa: E402
from app.siem.models.event_search import EventSearchColumns  # noqa: E402
from app.siem.models.event_search import EventSearchColumnTemplate  # noqa: E402
from app.siem.models.event_search import EventSearchRecentQuery  # noqa: E402
from app.siem.models.event_search import EventSearchSavedQuery  # noqa: E402
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


RELATIVE = {
    "source_name": "Wazuh",
    "query": "rule_level:>=10",
    "time_mode": "relative",
    "time_amount": 24,
    "time_unit": "h",
    "page_size": 50,
}


async def check_memory(client, portal, admin):
    base = f"/siem/event_search/{CUST_A}"
    login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
    other_device = {"Authorization": f"Bearer {login.json()['access_token']}"}

    print("\n=== E) saved queries live on the server ===")
    empty = await client.get(base, headers=portal)
    check(
        "an empty memory to start with",
        empty.status_code == 200 and empty.json()["saved"] == [] and empty.json()["recent"] == [],
        empty.text[:120],
    )
    saved = await client.post(f"{base}/saved", json={**RELATIVE, "name": "  High level "}, headers=portal)
    body = saved.json()
    check("save: 200, a new one", saved.status_code == 200 and body["replaced"] is False, saved.text[:160])
    check(
        "save: the name trimmed, the search as given",
        body["saved"][0]["name"] == "High level" and body["saved"][0]["query"] == "rule_level:>=10",
    )
    found = (await client.get(base, headers=other_device)).json()["saved"]
    check("the other device finds it", [q["name"] for q in found] == ["High level"], str(found)[:160])
    again = await client.post(f"{base}/saved", json={**RELATIVE, "query": "rule_level:>=12", "name": "HIGH level"}, headers=other_device)
    body = again.json()
    check(
        "the same name in another case updates it, under the name as typed last",
        body["replaced"] is True and [(q["name"], q["query"]) for q in body["saved"]] == [("HIGH level", "rule_level:>=12")],
        str(body["saved"])[:200],
    )
    absolute = await client.post(
        f"{base}/saved",
        json={
            **RELATIVE,
            "name": "Incident window",
            "time_mode": "absolute",
            "time_from": "2026-10-01T08:00:00+02:00",
            "time_to": "2026-10-01T10:30:00+02:00",
        },
        headers=portal,
    )
    window = next((q for q in absolute.json().get("saved", []) if q["name"] == "Incident window"), {})
    check(
        "an absolute range keeps its instant, in UTC",
        (window.get("time_from"), window.get("time_to")) == ("2026-10-01T06:00:00Z", "2026-10-01T08:30:00Z"),
        str(window)[:200],
    )
    check("newest first", [q["name"] for q in absolute.json()["saved"]] == ["Incident window", "HIGH level"])
    bad = await client.post(f"{base}/saved", json={**RELATIVE, "name": "   "}, headers=portal)
    check("a blank name: 422", bad.status_code == 422, bad.text[:120])
    bad = await client.post(f"{base}/saved", json={**RELATIVE, "name": "x", "time_mode": "absolute"}, headers=portal)
    check("an absolute range without dates: 422", bad.status_code == 422, bad.text[:120])

    print("\n=== F) recent searches ===")
    await client.post(f"{base}/recent", json=RELATIVE, headers=portal)
    recent = (await client.post(f"{base}/recent", json={**RELATIVE, "page_size": 250}, headers=other_device)).json()["recent"]
    check("the same search twice, whatever the page size: once", len(recent) == 1 and recent[0]["page_size"] == 250, str(recent)[:160])
    for n in range(12):
        recent = (await client.post(f"{base}/recent", json={**RELATIVE, "query": f"q{n}"}, headers=portal)).json()["recent"]
    check(
        "the last ten, newest first",
        [r["query"] for r in recent] == [f"q{n}" for n in range(11, 1, -1)],
        str([r["query"] for r in recent]),
    )
    found = (await client.get(base, headers=other_device)).json()["recent"]
    check("the other device sees the same list", [r["query"] for r in found] == [r["query"] for r in recent])
    cleared = await client.delete(f"{base}/recent", headers=other_device)
    check("clear: none left, the saved ones kept", cleared.json()["recent"] == [] and len(cleared.json()["saved"]) == 2, cleared.text[:160])

    print("\n=== G) columns per source ===")
    picked = [{"key": "agent_name", "label": "Host"}, {"key": "timestamp", "label": " "}]
    response = await client.put(f"{base}/columns", json={"source_name": "Wazuh", "columns": picked}, headers=portal)
    check("set: 200", response.status_code == 200, response.text[:160])
    columns = (await client.get(base, headers=other_device)).json()["columns"]
    check(
        "the other device finds them, a blank header read as the field",
        columns == {"Wazuh": [{"key": "agent_name", "label": "Host"}, {"key": "timestamp", "label": "timestamp"}]},
        str(columns),
    )
    await client.put(f"{base}/columns", json={"source_name": "Office", "columns": [{"key": "user", "label": "User"}]}, headers=portal)
    response = await client.put(f"{base}/columns", json={"source_name": "Wazuh", "columns": None}, headers=other_device)
    check(
        "none: back to the source's layout, the other source kept",
        list(response.json()["columns"]) == ["Office"],
        str(response.json()["columns"]),
    )

    print("\n=== K) column templates ===")
    triage = [{"key": "agent_name", "label": "Host"}, {"key": "rule_level", "label": "Level"}]
    response = await client.post(f"{base}/templates", json={"source_name": "Wazuh", "name": " Triage ", "columns": triage}, headers=portal)
    body = response.json()
    check("save: 200, a new one", response.status_code == 200 and body["replaced"] is False, response.text[:160])
    found = (await client.get(base, headers=other_device)).json()["templates"]
    check(
        "the other device finds it, named and in order",
        [(t["source_name"], t["name"], t["columns"]) for t in found] == [("Wazuh", "Triage", triage)],
        str(found)[:200],
    )
    response = await client.post(
        f"{base}/templates",
        json={"source_name": "Wazuh", "name": "TRIAGE", "columns": [{"key": "data_srcip", "label": ""}]},
        headers=other_device,
    )
    templates = response.json()["templates"]
    check(
        "the same name, in another case, updates it",
        response.json()["replaced"] is True
        and [(t["name"], t["columns"]) for t in templates] == [("TRIAGE", [{"key": "data_srcip", "label": "data_srcip"}])],
        str(templates)[:200],
    )
    await client.post(f"{base}/templates", json={"source_name": "Office", "name": "Triage", "columns": triage}, headers=portal)
    templates = (
        await client.post(f"{base}/templates", json={"source_name": "Wazuh", "name": "Audit", "columns": triage}, headers=portal)
    ).json()["templates"]
    check(
        "a name is per source; listed by source, then name",
        [(t["source_name"], t["name"]) for t in templates] == [("Office", "Triage"), ("Wazuh", "Audit"), ("Wazuh", "TRIAGE")],
        str([(t["source_name"], t["name"]) for t in templates]),
    )
    check(
        "a template without columns: 422",
        (await client.post(f"{base}/templates", json={"source_name": "Wazuh", "name": "x", "columns": []}, headers=portal)).status_code
        == 422,
    )
    for n in range(18):
        response = await client.post(
            f"{base}/templates",
            json={"source_name": "Wazuh", "name": f"T{n:02}", "columns": triage},
            headers=portal,
        )
    check("the twentieth on a source: saved", response.status_code == 200, response.text[:120])
    over = await client.post(f"{base}/templates", json={"source_name": "Wazuh", "name": "One too many", "columns": triage}, headers=portal)
    check("the next one: 409, nothing dropped", over.status_code == 409 and "delete one" in over.text, over.text[:160])
    check(
        "another source still has room",
        (
            await client.post(f"{base}/templates", json={"source_name": "Office", "name": "Second", "columns": triage}, headers=portal)
        ).status_code
        == 200,
    )
    audit = next(t["id"] for t in (await client.get(base, headers=portal)).json()["templates"] if t["name"] == "Audit")
    check("another user cannot delete it: 404", (await client.delete(f"{base}/templates/{audit}", headers=admin)).status_code == 404)
    check(
        "nor see it",
        (await client.get(base, headers=admin)).json()["templates"] == [],
    )
    check(
        "another customer: 403",
        (
            await client.post(
                f"/siem/event_search/{CUST_B}/templates",
                json={"source_name": "Wazuh", "name": "x", "columns": triage},
                headers=portal,
            )
        ).status_code
        == 403,
    )
    response = await client.delete(f"{base}/templates/{audit}", headers=portal)
    check("delete: 200, gone", response.status_code == 200 and all(t["id"] != audit for t in response.json()["templates"]))
    check("deleting it again: 404", (await client.delete(f"{base}/templates/{audit}", headers=portal)).status_code == 404)

    print("\n=== H) at most 50 saved queries per customer ===")
    for n in range(48):
        response = await client.post(f"{base}/saved", json={**RELATIVE, "name": f"Query {n}"}, headers=portal)
    check("the fiftieth: saved", response.status_code == 200 and len(response.json()["saved"]) == 50, response.text[:120])
    over = await client.post(f"{base}/saved", json={**RELATIVE, "name": "One too many"}, headers=portal)
    check("the next one: 409, nothing dropped", over.status_code == 409 and "delete one" in over.text, over.text[:160])
    check(
        "an existing name still updates",
        (await client.post(f"{base}/saved", json={**RELATIVE, "name": "Query 3"}, headers=portal)).status_code == 200,
    )
    memory = (await client.get(base, headers=portal)).json()
    victim = next(q["id"] for q in memory["saved"] if q["name"] == "Query 0")
    response = await client.delete(f"{base}/saved/{victim}", headers=portal)
    check("delete: 200, one less", response.status_code == 200 and len(response.json()["saved"]) == 49)
    check(
        "then there is room again",
        (await client.post(f"{base}/saved", json={**RELATIVE, "name": "One too many"}, headers=portal)).status_code == 200,
    )
    check("deleting it again: 404", (await client.delete(f"{base}/saved/{victim}", headers=portal)).status_code == 404)
    one_left = next(q["id"] for q in (await client.get(base, headers=portal)).json()["saved"] if q["name"] == "Query 1")
    await client.delete(f"{base}/saved/{one_left}", headers=portal)
    race = await asyncio.gather(
        client.post(f"{base}/saved", json={**RELATIVE, "name": "From this device"}, headers=portal),
        client.post(f"{base}/saved", json={**RELATIVE, "name": "From that device"}, headers=other_device),
    )
    count = len((await client.get(base, headers=portal)).json()["saved"])
    check(
        "two devices racing for the last slot: one saves, the other is refused",
        sorted(r.status_code for r in race) == [200, 409] and count == 50,
        f"{[r.status_code for r in race]} {count}",
    )

    print("\n=== I) another user, another customer ===")
    theirs = (await client.get(base, headers=admin)).json()
    check("another user (an admin) sees none of it", theirs["saved"] == [] and theirs["columns"] == {}, str(theirs)[:120])
    mine = next(q["id"] for q in memory["saved"] if q["name"] == "HIGH level")
    response = await client.delete(f"{base}/saved/{mine}", headers=admin)
    check("nor deletes it: 404", response.status_code == 404, response.text[:120])
    check("it is still there", any(q["id"] == mine for q in (await client.get(base, headers=portal)).json()["saved"]))
    other = f"/siem/event_search/{CUST_B}"
    for name, request in (
        ("read", client.get(other, headers=portal)),
        ("save", client.post(f"{other}/saved", json={**RELATIVE, "name": "x"}, headers=portal)),
        ("delete", client.delete(f"{other}/saved/{mine}", headers=portal)),
        ("remember", client.post(f"{other}/recent", json=RELATIVE, headers=portal)),
        ("clear", client.delete(f"{other}/recent", headers=portal)),
        ("columns", client.put(f"{other}/columns", json={"source_name": "Wazuh", "columns": None}, headers=portal)),
    ):
        response = await request
        check(f"another customer, {name}: 403", response.status_code == 403, f"{response.status_code} {response.text[:80]}")
    check("without a token: 401", (await client.get(base)).status_code == 401)


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

            await check_memory(client, portal, admin)

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
        left = 0
        for table in (EventSearchSavedQuery, EventSearchRecentQuery, EventSearchColumns, EventSearchColumnTemplate):
            left += await s.scalar(select(func.count()).select_from(table).where(table.customer_code.in_([CUST_A, CUST_B])))
    print("\n=== J) deleting the user and the customer ===")
    check("their saved, recent, column and template rows went with them", left == 0, str(left))
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
