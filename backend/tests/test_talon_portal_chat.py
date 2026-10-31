"""Talon chat in the Customer Portal, CoPilot's side (talon-analyst SPEC D97, §5.3; plan PC-3).

Real routers, a real in-memory database, real request parsing; talon-analyst is ``FakeTalon``
(``tests/talon_portal_chat_support.py``). Pinned here:

- the settings: off by default; read by admins and analysts; written by an admin only (by token and
  database role), validated (the chat needs AI reports and a daily limit; the per-user limit at most
  the customer's; 1 to 100,000), ``version`` bumped on every write, audited with old and new values;
- the cascade: AI reports off turns the chat off (bumped, audited); AI reports on again doesn't;
- availability: the switch, the limit, AI reports, CoPilot's "Talon v2" setting and talon-analyst's
  ``config.portal_chat``; drafts and analyses not for a read-only user;
- the portal proxy: the switch on every route, off and on, and turned off between two requests; the
  portal identity headers (and never the browser's); only ``/v2/portal/`` is forwarded; SOC roles
  refused; refusals carry a code;
- the draft submit: looking first (a filed draft is reported, nothing filed), claim true and false,
  an orphan, a filing in progress, every refusal code, "drafted with Talon";
- the lookup meter: the service account only, the portal user check, ``ioc_off``,
  ``ioc_in_progress``, ``ioc_limit``, the row written, completing it;
- the review proxy: admins, analysts and responders of the customer with unrestricted tags.

Run with: cd backend && python -m pytest tests/test_talon_portal_chat.py
"""

import asyncio
import json

import httpx
import pytest

from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.auth.models.users import UserTagAccess
from app.connectors.talon.services.identity import PORTAL_IDENTITY_HEADERS
from app.connectors.talon.utils import v2_client
from app.customer_portal.services import talon_chat
from app.db.universal_models import CustomerPortalChatSettings
from app.db.universal_models import CustomerPortalIocLookup
from app.db.universal_models import CustomerPortalSocRequest
from app.db.universal_models import CustomerPortalSocRequestSettings
from app.incidents.models import AlertTag
from app.incidents.models import CaseComment
from app.incidents.models import Comment
from app.incidents.models import TagAccessSettings
from tests.talon_portal_chat_support import ACME
from tests.talon_portal_chat_support import GLOBEX
from tests.talon_portal_chat_support import QUESTION
from tests.talon_portal_chat_support import FakeTalon
from tests.talon_portal_chat_support import a_while_ago
from tests.talon_portal_chat_support import as_user
from tests.talon_portal_chat_support import call
from tests.talon_portal_chat_support import rows
from tests.talon_portal_chat_support import set_chat

BASE = "/customer_portal/talon_chat"
SETTINGS = f"{BASE}/settings/{ACME}"
ON = {"portal_chat_enabled": True, "log_search_enabled": False, "daily_message_limit": 200, "user_daily_message_limit": 50}


def chat_actions(audit_rows):
    return [row for row in audit_rows if row.action == "talon_portal_chat.update"]


# ── the settings ──────────────────────────────────────────────────────────────


def test_off_by_default_with_the_proposed_limits():
    async def scenario(client, ctx):
        return await client.get(SETTINGS, headers=as_user("ana"))

    response = call(scenario, chat=False)
    assert response.status_code == 200
    body = response.json()
    assert body["settings"] == {
        "customer_code": ACME,
        "portal_chat_enabled": False,
        "log_search_enabled": False,
        "daily_message_limit": None,
        "user_daily_message_limit": None,
        "version": None,
        "updated_at": None,
        "updated_by": None,
    }
    assert body["ai_reports_enabled"] is True
    assert body["proposed"] == {"daily_message_limit": 200, "user_daily_message_limit": 50}
    assert response.headers["cache-control"] == "no-store"


def test_only_an_admin_writes_and_every_write_bumps_the_version_and_is_audited(audit_rows):
    async def scenario(client, ctx):
        analyst = await client.put(SETTINGS, json=ON, headers=as_user("ana"))
        demoted = await client.put(SETTINGS, json=ON, headers=as_user("demoted"))
        portal = await client.put(SETTINGS, json=ON, headers=as_user("jane"))
        first = await client.put(SETTINGS, json=ON, headers=as_user("admin"))
        second = await client.put(SETTINGS, json={**ON, "log_search_enabled": True}, headers=as_user("admin"))
        other_customer = await client.get(f"{BASE}/settings/{GLOBEX}", headers=as_user("ana"))
        unknown = await client.put(f"{BASE}/settings/NOPE", json=ON, headers=as_user("admin"))
        stored = await rows(ctx.db, CustomerPortalChatSettings, CustomerPortalChatSettings.customer_code == ACME)
        return analyst, demoted, portal, first, second, other_customer, unknown, stored

    analyst, demoted, portal, first, second, other_customer, unknown, stored = call(scenario, chat=False)
    assert (analyst.status_code, demoted.status_code, portal.status_code) == (403, 403, 403)
    assert demoted.json() == {"detail": "only an admin may change the portal chat settings", "code": "admin_only"}
    assert first.status_code == 200 and first.json()["settings"]["version"] == 1
    assert second.status_code == 200 and second.json()["settings"]["version"] == 2
    assert second.json()["settings"]["log_search_enabled"] is True and second.json()["settings"]["updated_by"] == 1
    assert other_customer.status_code == 403 and other_customer.json()["code"] == "customer_not_accessible"
    assert unknown.status_code == 404 and unknown.json() == {"detail": "customer not found", "code": "customer_not_found"}
    (row,) = stored
    assert (row.portal_chat_enabled, row.log_search_enabled, row.daily_message_limit, row.user_daily_message_limit, row.version) == (
        True,
        True,
        200,
        50,
        2,
    )
    audits = chat_actions(audit_rows)
    assert len(audits) == 2  # the refused writes changed nothing and recorded nothing
    assert (audits[0].actor_username, audits[0].customer_code, audits[0].entity_type) == ("admin", ACME, "customer_portal_chat_settings")
    assert audits[0].old_value == {
        "portal_chat_enabled": False,
        "log_search_enabled": False,
        "daily_message_limit": None,
        "user_daily_message_limit": None,
        "version": None,
    }
    assert audits[0].new_value == {**ON, "version": 1}
    assert audits[1].old_value == {**ON, "version": 1} and audits[1].new_value == {**ON, "log_search_enabled": True, "version": 2}


@pytest.mark.parametrize(
    "values, ai_reports, text",
    [
        ({**ON, "daily_message_limit": None, "user_daily_message_limit": None}, True, talon_chat.NEEDS_DAILY_LIMIT),
        (ON, False, talon_chat.NEEDS_AI_REPORTS),
        ({**ON, "user_daily_message_limit": 201}, True, talon_chat.USER_OVER_CUSTOMER),
        ({**ON, "daily_message_limit": 0}, True, talon_chat.LIMIT_RANGE),
        ({**ON, "daily_message_limit": 100_001}, True, talon_chat.LIMIT_RANGE),
        ({**ON, "portal_chat_enabled": False, "daily_message_limit": None}, True, talon_chat.USER_WITHOUT_CUSTOMER),
    ],
)
def test_the_validation_needs_ai_reports_and_a_daily_limit(values, ai_reports, text, audit_rows):
    async def scenario(client, ctx):
        response = await client.put(SETTINGS, json=values, headers=as_user("admin"))
        return response, await rows(ctx.db, CustomerPortalChatSettings)

    response, stored = call(scenario, chat=False, ai_reports=ai_reports)
    assert response.status_code == 422
    assert response.json() == {"detail": text, "code": "invalid_request"}
    assert stored == [] and chat_actions(audit_rows) == []


@pytest.mark.parametrize(
    "body",
    [
        {**ON, "daily_message_limit": "200"},
        {**ON, "portal_chat_enabled": 1},
        {k: v for k, v in ON.items() if k != "log_search_enabled"},
        {**ON, "customer_code": GLOBEX},
    ],
)
def test_a_body_that_isnt_the_settings_is_an_invalid_request(body):
    async def scenario(client, ctx):
        return await client.put(SETTINGS, json=body, headers=as_user("admin"))

    response = call(scenario, chat=False)
    assert response.status_code == 422 and response.json() == {"detail": "invalid request", "code": "invalid_request"}


def test_the_chat_may_be_off_with_limits_and_log_search_set():
    async def scenario(client, ctx):
        return await client.put(SETTINGS, json={**ON, "portal_chat_enabled": False, "log_search_enabled": True}, headers=as_user("admin"))

    response = call(scenario, chat=False, ai_reports=False)
    assert response.status_code == 200 and response.json()["settings"]["portal_chat_enabled"] is False


# ── the cascade ───────────────────────────────────────────────────────────────


def test_turning_ai_reports_off_turns_the_chat_off_and_on_again_does_not(audit_rows):
    async def scenario(client, ctx):
        off = await client.put(f"/customer_portal/ai_reports/settings/{ACME}", json={"enabled": False}, headers=as_user("admin"))
        after_off = (await rows(ctx.db, CustomerPortalChatSettings, CustomerPortalChatSettings.customer_code == ACME))[0]
        on = await client.put(f"/customer_portal/ai_reports/settings/{ACME}", json={"enabled": True}, headers=as_user("admin"))
        after_on = (await rows(ctx.db, CustomerPortalChatSettings, CustomerPortalChatSettings.customer_code == ACME))[0]
        globex = (await rows(ctx.db, CustomerPortalChatSettings, CustomerPortalChatSettings.customer_code == GLOBEX))[0]
        return off, after_off, on, after_on, globex

    off, after_off, on, after_on, globex = call(scenario)
    assert off.status_code == 200 and on.status_code == 200
    assert after_off.portal_chat_enabled is False and after_off.version == 4 and after_off.updated_by == 1
    assert after_off.daily_message_limit == 200  # only the switch
    assert after_on.portal_chat_enabled is False and after_on.version == 4
    assert globex.portal_chat_enabled is True and globex.version == 3
    (audit,) = chat_actions(audit_rows)
    assert audit.customer_code == ACME and audit.actor_username == "admin"
    assert audit.old_value["portal_chat_enabled"] is True and audit.old_value["version"] == 3
    assert audit.new_value["portal_chat_enabled"] is False and audit.new_value["version"] == 4
    assert "AI reports were turned off" in audit.details


def test_turning_ai_reports_off_when_the_chat_is_off_writes_nothing(audit_rows):
    async def scenario(client, ctx):
        await set_chat(ctx.db, portal_chat_enabled=False)
        await client.put(f"/customer_portal/ai_reports/settings/{ACME}", json={"enabled": False}, headers=as_user("admin"))
        return (await rows(ctx.db, CustomerPortalChatSettings, CustomerPortalChatSettings.customer_code == ACME))[0]

    row = call(scenario)
    assert row.version == 3 and chat_actions(audit_rows) == []


# ── availability ──────────────────────────────────────────────────────────────


def availability(client, user="jane", **params):
    return client.get(f"{BASE}/availability", params=params, headers=as_user(user))


def test_availability_reflects_the_switch_ai_reports_and_talon():
    talon = FakeTalon()

    async def scenario(client, ctx):
        answers = {"on": (await availability(client)).json()}
        await set_chat(ctx.db, portal_chat_enabled=False)
        answers["switch_off"] = (await availability(client)).json()
        await set_chat(ctx.db, portal_chat_enabled=True, daily_message_limit=None)
        answers["no_limit"] = (await availability(client)).json()
        await set_chat(ctx.db, daily_message_limit=200)
        talon_chat.clear_health_cache()
        talon.portal_chat = False
        answers["talon_off"] = (await availability(client)).json()
        answers["analyst"] = (await availability(client, "ana", customer_code=ACME)).json()
        other = await availability(client, customer_code=GLOBEX)
        return answers, other

    answers, other = call(scenario, talon=talon)
    assert answers["on"] == {
        "customer_code": ACME,
        "enabled": True,
        "log_search": False,
        "can_draft": True,
        "can_request_analysis": True,
        "success": True,
        "message": "Portal chat is available",
    }
    assert answers["switch_off"]["enabled"] is False and answers["no_limit"]["enabled"] is False
    assert answers["talon_off"]["enabled"] is False and answers["analyst"]["enabled"] is False
    assert other.status_code == 403 and other.json()["code"] == "customer_not_accessible"


def test_availability_needs_ai_reports_and_the_talon_v2_setting():
    async def scenario(client, ctx):
        return (await availability(client)).json()

    assert call(scenario, ai_reports=False)["enabled"] is False
    assert call(scenario, v2=False)["enabled"] is False


def test_talons_health_answer_is_cached_and_unknown_reads_as_off():
    talon = FakeTalon()

    async def scenario(client, ctx):
        await availability(client)
        await availability(client)
        asked = len([r for r in talon.requests if r.url.path == "/v2/health"])
        talon_chat.clear_health_cache()
        real = talon.handler
        talon.handler = lambda request: httpx.Response(503, json={"status": "starting"})
        unknown = (await availability(client)).json()
        talon.handler = real
        return asked, unknown

    asked, unknown = call(scenario, talon=talon)
    assert asked == 1
    assert unknown["enabled"] is False


def test_drafts_and_analyses_are_not_offered_to_a_read_only_user():
    async def scenario(client, ctx):
        return (await availability(client, "rory")).json()

    answer = call(scenario)
    assert answer["enabled"] is True and answer["can_draft"] is False and answer["can_request_analysis"] is False


def test_log_search_follows_its_switch():
    async def scenario(client, ctx):
        await set_chat(ctx.db, log_search_enabled=True)
        return (await availability(client)).json()

    assert call(scenario)["log_search"] is True


# ── the portal proxy: the switch, the identity, the prefix ─────────────────────


def proxy_routes(thread_id, draft_id):
    return [
        ("GET", f"{BASE}/threads", None),
        ("POST", f"{BASE}/threads", {"customer_code": ACME}),
        ("PATCH", f"{BASE}/threads/{thread_id}", {"title": "Renamed"}),
        ("DELETE", f"{BASE}/threads/{thread_id}", None),
        ("GET", f"{BASE}/threads/{thread_id}/messages", None),
        ("POST", f"{BASE}/threads/{thread_id}/feedback", {"run_id": "run-1", "rating": "up"}),
        ("POST", f"{BASE}/chat/{thread_id}", {"message": "What happened on HOST-A?"}),
        ("GET", f"{BASE}/drafts/{draft_id}", None),
        ("POST", f"{BASE}/drafts/{draft_id}/submit", {"question": QUESTION, "urgency": "normal"}),
        ("POST", f"{BASE}/drafts/{draft_id}/discard", None),
    ]


async def send(client, method, path, body, user="jane", headers=None):
    return await client.request(method, path, json=body, headers=as_user(user, **(headers or {})))


@pytest.mark.parametrize("off", ["switch", "no_limit", "ai_reports", "talon", "v2"])
def test_every_proxy_route_refuses_while_the_switch_is_off(off):
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread_id = talon.add_thread()
        draft_id = talon.add_draft("alert", ctx.ids.lonely)
        if off == "switch":
            await set_chat(ctx.db, portal_chat_enabled=False)
        elif off == "no_limit":
            await set_chat(ctx.db, daily_message_limit=None)
        elif off == "talon":
            talon.portal_chat = False
        answers = [await send(client, method, path, body) for method, path, body in proxy_routes(thread_id, draft_id)]
        return answers, list(talon.portal_requests())

    answers, forwarded = call(scenario, talon=talon, ai_reports=(off != "ai_reports"), v2=(off != "v2"))
    for response in answers:
        assert response.status_code == 403, response.text
        assert response.json() == {"detail": "portal chat is turned off for this customer", "code": "portal_off"}
    assert forwarded == []  # nothing reached talon-analyst's portal routes


def test_every_proxy_route_works_while_the_switch_is_on():
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread_id = talon.add_thread()
        draft_id = talon.add_draft("alert", ctx.ids.lonely)
        return [await send(client, method, path, body) for method, path, body in proxy_routes(thread_id, draft_id)]

    answers = call(scenario, talon=talon)
    statuses = [response.status_code for response in answers]
    assert statuses == [200, 201, 200, 200, 200, 204, 200, 200, 200, 409], [r.text for r in answers]
    # The stream passes through byte for byte, its error chunk's code included.
    chat = answers[6]
    assert chat.headers["content-type"].startswith("text/event-stream")
    assert chat.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert chat.content == talon.stream and b'"code":"portal_off"' in chat.content
    # The discard came after the submit: the draft was filed, so it can't be discarded.
    assert answers[9].json()["code"] == "draft_conflict"


def test_the_switch_turned_off_mid_way_refuses_the_next_request():
    talon = FakeTalon()

    async def scenario(client, ctx):
        created = await send(client, "POST", f"{BASE}/threads", {"customer_code": ACME})
        thread_id = created.json()["id"]
        first = await send(client, "POST", f"{BASE}/chat/{thread_id}", {"message": "hello"})
        await set_chat(ctx.db, portal_chat_enabled=False)
        second = await send(client, "POST", f"{BASE}/chat/{thread_id}", {"message": "and now?"})
        messages = await send(client, "GET", f"{BASE}/threads/{thread_id}/messages", None)
        chats = [r for r in talon.requests if r.url.path.startswith("/v2/portal/chat/")]
        return first, second, messages, chats

    first, second, messages, chats = call(scenario, talon=talon)
    assert first.status_code == 200
    assert second.status_code == 403 and second.json()["code"] == "portal_off"
    assert messages.status_code == 403 and messages.json()["code"] == "portal_off"
    assert len(chats) == 1


def test_a_thread_of_a_switched_off_customer_is_refused_while_another_customer_is_on():
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread_id = talon.add_thread(GLOBEX, owner="12")
        await set_chat(ctx.db, GLOBEX, portal_chat_enabled=False)
        chat = await send(client, "POST", f"{BASE}/chat/{thread_id}", {"message": "hi"}, user="multi")
        create = await send(client, "POST", f"{BASE}/threads", {"customer_code": GLOBEX}, user="multi")
        listed = await send(client, "GET", f"{BASE}/threads", None, user="multi")
        return chat, create, listed

    chat, create, listed = call(scenario, talon=talon)
    assert chat.status_code == 403 and chat.json()["code"] == "portal_off"
    assert create.status_code == 403 and create.json()["code"] == "portal_off"
    assert listed.status_code == 200  # talon-analyst marks the thread accessible: false


def test_the_portal_identity_headers_and_never_the_browsers():
    talon = FakeTalon()
    forged = {
        "X-Talon-User": "1",
        "X-Talon-Role": "admin",
        "X-Talon-Customers": "*",
        "X-Talon-Tags": "7",
        "X-Talon-Untagged": "false",
        "X-Talon-Read-Only": "",
        "X-Talon-Extra": "x",
    }

    async def scenario(client, ctx):
        await send(client, "GET", f"{BASE}/threads", None, user="multi", headers=forged)
        await send(client, "GET", f"{BASE}/threads", None, user="jane")
        return talon.portal_requests()

    multi, jane = call(scenario, talon=talon)
    for request, user, customers, read_only in ((multi, "12", "ACME,GLOBEX", "GLOBEX"), (jane, "10", "ACME", "")):
        talon_headers = {k.lower(): v for k, v in request.headers.items() if k.lower().startswith("x-talon-")}
        assert talon_headers == {
            "x-talon-user": user,
            "x-talon-role": "customer",
            "x-talon-customers": customers,
            "x-talon-tags": "*",
            "x-talon-untagged": "true",
            "x-talon-read-only": read_only,
        }
        assert request.headers["x-api-key"] == "dummy-talon-key"


def test_a_new_thread_takes_the_users_customer_never_the_bodys_identity():
    talon = FakeTalon()

    async def scenario(client, ctx):
        other = await send(client, "POST", f"{BASE}/threads", {"customer_code": GLOBEX})
        unknown_field = await send(client, "POST", f"{BASE}/threads", {"customer_code": ACME, "user_id": 1})
        foreign_alert = await send(client, "POST", f"{BASE}/threads", {"customer_code": ACME, "alert_id": ctx.ids.globex_alert})
        good = await send(client, "POST", f"{BASE}/threads", {"customer_code": ACME, "title": "HOST-A", "alert_id": ctx.ids.lonely})
        creates = [json.loads(r.content) for r in talon.requests if r.method == "POST" and r.url.path == "/v2/portal/threads"]
        return other, unknown_field, foreign_alert, good, creates, ctx.ids.lonely

    other, unknown_field, foreign_alert, good, creates, alert_id = call(scenario, talon=talon)
    assert other.status_code == 403 and other.json()["code"] == "customer_not_accessible"
    assert unknown_field.status_code == 422 and unknown_field.json()["code"] == "invalid_request"
    assert foreign_alert.status_code == 404 and foreign_alert.json()["code"] == "alert_not_found"
    assert good.status_code == 201
    (create,) = creates
    assert create == {"customer_code": ACME, "title": "HOST-A", "alert_id": alert_id, "language": "en"}


def test_a_new_threads_language_is_the_portals_when_the_user_may_have_it():
    from app.db.universal_models import CustomerPortalLanguageSettings

    talon = FakeTalon()

    async def scenario(client, ctx):
        async with ctx.db.session() as s:
            s.add(CustomerPortalLanguageSettings(customer_code=ACME, languages=["en", "de"]))
            await s.commit()
        answers = []
        for language in ("de", "fr", "xx-not-a-locale", None, "en"):
            body = {"customer_code": ACME, **({"language": language} if language is not None else {})}
            answers.append((await send(client, "POST", f"{BASE}/threads", body)).status_code)
        too_long = await send(client, "POST", f"{BASE}/threads", {"customer_code": ACME, "language": "x" * 17})
        creates = [json.loads(r.content)["language"] for r in talon.requests if r.method == "POST" and r.url.path == "/v2/portal/threads"]
        return answers, too_long, creates

    answers, too_long, creates = call(scenario, talon=talon)
    assert answers == [201] * 5
    # Available to the user: kept; not available (fr is a portal locale, but not this customer's), or absent: the portal language.
    assert creates == ["de", "en", "en", "en", "en"]
    assert too_long.status_code == 422 and too_long.json()["code"] == "invalid_request"


def test_soc_roles_and_unknown_tokens_are_refused_on_the_portal_routes():
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread_id = talon.add_thread()
        draft_id = talon.add_draft("alert", ctx.ids.lonely)
        answers = []
        for user in ("admin", "ana", "resp", "talon-analyst"):
            answers += [await send(client, method, path, body, user=user) for method, path, body in proxy_routes(thread_id, draft_id)]
        return answers, talon.portal_requests()

    answers, forwarded = call(scenario, talon=talon)
    assert {response.status_code for response in answers} == {403}
    assert forwarded == []


def test_only_the_portal_prefix_is_forwarded():
    portal = {name: "x" for name in PORTAL_IDENTITY_HEADERS} | {"X-Talon-Role": "customer"}
    soc = {name: "x" for name in PORTAL_IDENTITY_HEADERS if name != "X-Talon-Read-Only"} | {"X-Talon-Role": "analyst"}
    thread = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"
    for path in (f"/v2/portal/threads/{thread}", "/v2/portal/threads", f"/v2/portal/chat/{thread}"):
        v2_client.check_identity_path(portal, path)
    for path in (
        "/v2/threads",
        "/v2/portal-review/threads",
        "/v2/portal",
        "/v2/portal/",
        "/v2/portal/../threads",
        "/v2/portal/threads/x?y=1",
        "/v2/portal/threads/%2e%2e",
        "/v2/portal//threads",
        "/v2/actions/1/approve",
    ):
        with pytest.raises(ValueError):
            v2_client.check_identity_path(portal, path)
    # A SOC identity never goes to the portal routes, and the portal role never with a SOC identity.
    with pytest.raises(ValueError):
        v2_client.check_identity_path(soc, "/v2/portal/threads")
    with pytest.raises(ValueError):
        v2_client.check_identity_path(soc | {"X-Talon-Role": "customer"}, "/v2/threads")
    v2_client.check_identity_path(soc, "/v2/portal-review/threads")


def test_every_upstream_request_of_the_portal_routes_is_under_the_portal_prefix():
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread_id = talon.add_thread()
        draft_id = talon.add_draft("case", ctx.ids.open_case)
        for method, path, body in proxy_routes(thread_id, draft_id):
            await send(client, method, path, body)
        return talon.portal_requests()

    forwarded = call(scenario, talon=talon)
    assert forwarded and all(r.url.path.startswith("/v2/portal/") for r in forwarded)


@pytest.mark.parametrize("bad", ["not-a-uuid", "..%2F..%2Fthreads", "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e%3Fx%3D1"])
def test_a_path_id_that_isnt_an_id_is_never_forwarded(bad):
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread = await send(client, "POST", f"{BASE}/chat/{bad}", {"message": "hi"})
        draft = await send(client, "GET", f"{BASE}/drafts/{bad}", None)
        return thread, draft, talon.portal_requests()

    thread, draft, forwarded = call(scenario, talon=talon)
    # Refused as an unknown thread or draft, or (an escaped slash) matching no route at all.
    assert thread.status_code == 404 and thread.json().get("code", "thread_not_found") == "thread_not_found"
    assert draft.status_code == 404 and draft.json().get("code", "draft_not_found") == "draft_not_found"
    assert forwarded == []


def test_talons_refusals_pass_through_with_their_code_and_a_bad_body_is_coded():
    talon = FakeTalon()

    async def scenario(client, ctx):
        other_users = talon.add_thread(owner="99")
        not_found = await send(client, "POST", f"{BASE}/chat/{other_users}", {"message": "hi"})
        bad_json = await client.post(f"{BASE}/chat/{other_users}", content=b"{not json", headers=as_user("jane"))
        too_big = await client.post(
            f"{BASE}/chat/{other_users}",
            content=b"x" * (1024 * 1024 + 1),
            headers=as_user("jane", **{"content-type": "application/json"}),
        )
        submit_message = await send(
            client,
            "POST",
            f"{BASE}/chat/{talon.add_thread()}",
            {
                "trigger": "submit-message",
                "id": "x",
                "messages": [{"id": "m1", "role": "user", "parts": [{"type": "text", "text": "hey"}]}],
            },
        )
        sent = [json.loads(r.content) for r in talon.requests if r.url.path.startswith("/v2/portal/chat/")]
        return not_found, bad_json, too_big, submit_message, sent

    not_found, bad_json, too_big, submit_message, sent = call(scenario, talon=talon)
    assert not_found.status_code == 404 and not_found.json() == {"detail": "thread not found", "code": "thread_not_found"}
    assert bad_json.status_code == 422 and bad_json.json()["code"] == "invalid_request"
    assert too_big.status_code == 413 and too_big.json()["code"] == "body_too_large"
    assert submit_message.status_code == 200
    (body,) = sent
    assert body["trigger"] == "submit-message" and body["messages"][0]["parts"] == [{"type": "text", "text": "hey"}]
    assert body["id"] != "x"  # the thread id is the path's, never the body's


# ── the draft submit ──────────────────────────────────────────────────────────


def submit(client, draft_id, user="jane", **body):
    return client.post(f"{BASE}/drafts/{draft_id}/submit", json={"question": QUESTION, "urgency": "high", **body}, headers=as_user(user))


def test_an_alert_draft_is_claimed_filed_on_the_alerts_case_and_reported():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.linked)
        response = await submit(client, draft_id)
        filed = await rows(ctx.db, CustomerPortalSocRequest)
        comments = await rows(ctx.db, CaseComment, CaseComment.case_id == ctx.ids.open_case)
        listed = await client.get("/customer_portal/soc_requests", headers=as_user("ana"))
        return draft_id, response, filed, comments, listed, ctx

    draft_id, response, filed, comments, listed, ctx = call(scenario, talon=talon)
    assert response.status_code == 200, response.text
    (row,) = filed
    assert response.json() == {"request_id": row.id}
    assert (row.talon_draft_id, row.case_id, row.origin_alert_id, row.urgency, row.question) == (
        draft_id,
        ctx.ids.open_case,
        ctx.ids.linked,
        "high",
        QUESTION,
    )
    (comment,) = comments
    assert comment.comment.startswith("Drafted with Talon, reviewed and sent by the customer.\nQuestion for the SOC (urgency: High)")
    claim = [json.loads(r.content) for r in talon.requests if r.url.path.endswith("/claim")]
    assert claim == [{"urgency": "high", "file_on": "case"}]
    assert talon.outcomes == [(draft_id, {"outcome": "submitted", "copilot_ref": str(row.id)})]
    assert listed.json()["requests"][0]["drafted_with_talon"] is True


def test_an_alert_draft_filed_on_the_alert_and_a_case_draft_on_the_case():
    talon = FakeTalon()

    async def scenario(client, ctx):
        on_alert = talon.add_draft("alert", ctx.ids.lonely)
        on_case = talon.add_draft("case", ctx.ids.open_case)
        first = await submit(client, on_alert, file_on="alert")
        second = await submit(client, on_case, file_on="alert")  # ignored for a case draft
        alert_comments = await rows(ctx.db, Comment, Comment.alert_id == ctx.ids.lonely)
        filed = {row.talon_draft_id: row for row in await rows(ctx.db, CustomerPortalSocRequest)}
        claims = [json.loads(r.content) for r in talon.requests if r.url.path.endswith("/claim")]
        return on_alert, on_case, first, second, alert_comments, filed, claims

    on_alert, on_case, first, second, alert_comments, filed, claims = call(scenario, talon=talon)
    assert first.status_code == 200 and second.status_code == 200
    assert filed[on_alert].alert_id is not None and filed[on_alert].case_id is None
    assert filed[on_case].case_id is not None and filed[on_case].alert_id is None
    assert [c.comment.splitlines()[0] for c in alert_comments] == ["Drafted with Talon, reviewed and sent by the customer."]
    assert claims == [{"urgency": "high", "file_on": "alert"}, {"urgency": "high"}]


def test_a_draft_filed_already_is_reported_and_never_claimed_or_filed_again():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.linked)
        first = await submit(client, draft_id)
        talon.drafts[draft_id]["status"] = "submitting"  # say the outcome was lost
        talon.outcomes.clear()
        claims_before = len([r for r in talon.requests if r.url.path.endswith("/claim")])
        second = await submit(client, draft_id, question="An edited question that must not be filed")
        claims_after = len([r for r in talon.requests if r.url.path.endswith("/claim")])
        filed = await rows(ctx.db, CustomerPortalSocRequest)
        return draft_id, first, second, claims_before, claims_after, filed

    draft_id, first, second, claims_before, claims_after, filed = call(scenario, talon=talon)
    assert first.status_code == 200 and second.status_code == 200
    assert second.json() == first.json()
    assert claims_after == claims_before  # looked first: no claim
    assert len(filed) == 1 and filed[0].question == QUESTION
    assert talon.outcomes == [(draft_id, {"outcome": "submitted", "copilot_ref": str(filed[0].id)})]


def test_a_filed_draft_is_reported_even_when_copilots_own_rules_would_refuse_now():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.linked)
        first = await submit(client, draft_id)
        async with ctx.db.session() as s:  # the SOC requests switched off since, and the cooldown runs
            await s.execute(CustomerPortalSocRequestSettings.__table__.update().values(enabled=False))
            await s.commit()
        second = await submit(client, draft_id)
        return first, second

    first, second = call(scenario, talon=talon)
    assert second.status_code == 200 and second.json() == first.json()


def test_a_claim_that_says_false_files_nothing_and_is_a_conflict():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.linked, status="submitting")
        response = await submit(client, draft_id)
        return response, await rows(ctx.db, CustomerPortalSocRequest)

    response, filed = call(scenario, talon=talon)
    assert response.status_code == 409 and response.json() == {"detail": "this draft was already decided", "code": "draft_conflict"}
    assert filed == []


def test_an_orphan_is_deleted_and_the_draft_filed_again():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.lonely)
        async with ctx.db.session() as s:
            s.add(
                CustomerPortalSocRequest(
                    customer_code=ACME,
                    question=QUESTION,
                    urgency="high",
                    status="open",
                    requested_by="jane",
                    requested_by_user_id=10,
                    requested_at=a_while_ago(6),
                    talon_draft_id=draft_id,
                ),
            )
            await s.commit()
        response = await submit(client, draft_id)
        return draft_id, response, await rows(ctx.db, CustomerPortalSocRequest)

    draft_id, response, filed = call(scenario, talon=talon)
    assert response.status_code == 200, response.text
    (row,) = filed
    assert row.talon_draft_id == draft_id and row.comment_id is not None and response.json() == {"request_id": row.id}


def test_a_draft_being_filed_by_another_request_is_a_conflict():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.lonely)
        async with ctx.db.session() as s:
            s.add(
                CustomerPortalSocRequest(
                    customer_code=ACME,
                    question=QUESTION,
                    urgency="high",
                    status="open",
                    requested_by="jane",
                    requested_at=a_while_ago(1),
                    talon_draft_id=draft_id,
                ),
            )
            await s.commit()
        response = await submit(client, draft_id)
        return response, [r for r in talon.requests if r.url.path.endswith("/claim")]

    response, claims = call(scenario, talon=talon)
    assert response.status_code == 409 and response.json()["code"] == "draft_conflict"
    assert claims == []


def test_a_conflict_on_the_unique_draft_id_reports_the_other_requests_row(monkeypatch):
    from app.customer_portal.services import soc_requests

    talon = FakeTalon()
    seen = {}

    async def scenario(client, ctx):
        draft_id = talon.add_draft("case", ctx.ids.open_case)
        real = soc_requests._reserve

        async def racing(*args, **kwargs):
            # Another request files the draft between the look and this insert.
            async with ctx.db.session() as s:
                other = CustomerPortalSocRequest(
                    customer_code=ACME,
                    question="theirs",
                    urgency="low",
                    status="open",
                    requested_by="jane",
                    requested_at=a_while_ago(0),
                    talon_draft_id=draft_id,
                    comment_id=999,
                )
                s.add(other)
                await s.commit()
                seen["other"] = other.id
            return await real(*args, **kwargs)

        monkeypatch.setattr(soc_requests, "_reserve", racing)
        response = await submit(client, draft_id)
        return draft_id, response, await rows(ctx.db, CustomerPortalSocRequest)

    draft_id, response, filed = call(scenario, talon=talon)
    assert response.status_code == 200 and response.json() == {"request_id": seen["other"]}
    assert len(filed) == 1
    assert talon.outcomes == [(draft_id, {"outcome": "submitted", "copilot_ref": str(seen["other"])})]


@pytest.mark.parametrize(
    "setup, code, status, outcome",
    [
        ("read_only", "read_only", 403, None),
        ("not_mine", "draft_not_found", 404, None),
        ("expired", "draft_expired", 409, None),
        ("decided", "draft_conflict", 409, None),
        ("soc_off", "soc_requests_off", 403, "soc_requests_off"),
        ("limit", "soc_request_limit", 429, "soc_request_limit"),
        ("cooldown", "soc_request_cooldown", 429, "soc_request_cooldown"),
        ("bad_question", "invalid_question", 422, None),
        ("gone", "not_found", 404, "not_found"),
        ("broken", "internal_failure", 500, "internal_failure"),
        ("portal_off", "portal_off", 403, None),
    ],
)
def test_every_refusal_of_the_submit_has_its_code(setup, code, status, outcome, monkeypatch):
    talon = FakeTalon()

    async def scenario(client, ctx):
        user, body = "jane", {}
        draft_id = talon.add_draft("alert", ctx.ids.linked)
        if setup == "read_only":
            user = "rory"
            talon.drafts[draft_id]["owner"] = "11"
        elif setup == "not_mine":
            talon.drafts[draft_id]["owner"] = "11"
        elif setup == "expired":
            talon.claim_override = lambda draft: httpx.Response(409, json={"detail": "this draft expired", "code": "draft_expired"})
        elif setup == "decided":
            talon.drafts[draft_id]["status"] = "discarded"
        elif setup == "soc_off":
            async with ctx.db.session() as s:
                await s.execute(CustomerPortalSocRequestSettings.__table__.update().values(enabled=False))
                await s.commit()
        elif setup == "limit":
            async with ctx.db.session() as s:
                await s.execute(CustomerPortalSocRequestSettings.__table__.update().values(daily_request_limit=1))
                s.add(CustomerPortalSocRequest(customer_code=ACME, question="q", status="open", requested_by="jane", case_id=None))
                await s.commit()
        elif setup == "cooldown":
            async with ctx.db.session() as s:
                s.add(
                    CustomerPortalSocRequest(customer_code=ACME, question="q", status="open", requested_by="jane", alert_id=ctx.ids.linked),
                )
                await s.commit()
        elif setup == "bad_question":
            body = {"question": "hidden‮characters"}
        elif setup == "gone":
            talon.drafts[draft_id]["target"]["id"] = 999_999
        elif setup == "broken":
            from app.customer_portal.services import soc_requests

            async def fail(*args, **kwargs):
                raise RuntimeError("the comment could not be written")

            monkeypatch.setattr(soc_requests, "_comment_on_case", fail)
        elif setup == "portal_off":
            await set_chat(ctx.db, portal_chat_enabled=False)
        response = await submit(client, draft_id, user=user, **body)
        filed = [row for row in await rows(ctx.db, CustomerPortalSocRequest) if row.talon_draft_id == draft_id]
        return draft_id, response, filed

    draft_id, response, filed = call(scenario, talon=talon)
    assert response.status_code == status, response.text
    assert response.json()["code"] == code
    assert filed == []
    if outcome is None:
        assert talon.outcomes == []
    else:
        assert talon.outcomes == [(draft_id, {"outcome": "failed", "failure": outcome})]
        assert talon.drafts[draft_id]["status"] == "pending"  # the customer may try again


def test_discarding_a_draft_posts_the_outcome():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.lonely)
        response = await client.post(f"{BASE}/drafts/{draft_id}/discard", headers=as_user("jane"))
        return draft_id, response

    draft_id, response = call(scenario, talon=talon)
    assert response.status_code == 200 and response.json()["status"] == "discarded"
    assert talon.outcomes == [(draft_id, {"outcome": "discarded"})]


# ── the lookup meter ──────────────────────────────────────────────────────────

METER = "/talon/v2/portal/ioc_lookups"


def reserve(client, user="talon-analyst", **body):
    return client.post(METER, json={"customer_code": ACME, "user_id": 10, "value": "8.8.8.8", **body}, headers=as_user(user))


def test_the_meter_is_the_talon_service_accounts_only():
    async def scenario(client, ctx):
        answers = [await reserve(client, user) for user in ("ana", "admin", "jane", "resp")]
        complete = await client.post(f"{METER}/1/complete", json={"answered": True}, headers=as_user("ana"))
        return answers, complete, await rows(ctx.db, CustomerPortalIocLookup)

    answers, complete, stored = call(scenario)
    assert [r.status_code for r in answers] == [403, 403, 403, 403]
    assert complete.status_code == 403 and stored == []


def test_the_meter_reserves_one_lookup_for_a_portal_user_of_the_customer():
    async def scenario(client, ctx):
        reserved = await reserve(client)
        stored = await rows(ctx.db, CustomerPortalIocLookup)
        return reserved, stored

    reserved, stored = call(scenario)
    assert reserved.status_code == 201
    (row,) = stored
    assert reserved.json() == {"lookup_id": row.id}
    assert (row.customer_code, row.requested_by_user_id, row.completed_at) == (ACME, 10, None)
    from app.customer_portal.services import ioc_enrichment
    from app.customer_portal.services import ioc_enrichment_sources as sources

    assert row.value_sha256 == ioc_enrichment.value_digest(sources.classify("8.8.8.8")[1])


@pytest.mark.parametrize(
    "body",
    [
        {"user_id": 2},  # an analyst, not a portal user
        {"user_id": 13},  # a portal user of another customer
        {"user_id": 404},  # nobody
        {"customer_code": "NOPE"},
    ],
)
def test_the_meter_checks_the_portal_user(body):
    async def scenario(client, ctx):
        return await reserve(client, **body), await rows(ctx.db, CustomerPortalIocLookup)

    response, stored = call(scenario)
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert stored == []


def test_the_meters_refusals():
    async def scenario(client, ctx):
        first = await reserve(client)
        in_progress = await reserve(client)
        other_value = await reserve(client, value="evil.example")
        limited = await reserve(client, value="third.example")
        return first, in_progress, other_value, limited

    first, in_progress, other_value, limited = call(scenario, ioc_limit=2)
    assert first.status_code == 201 and other_value.status_code == 201
    assert in_progress.status_code == 409 and in_progress.json() == {
        "detail": "this indicator is being checked already; try again in a moment",
        "code": "ioc_in_progress",
    }
    assert limited.status_code == 429 and limited.json()["code"] == "ioc_limit"

    async def off(client, ctx):
        return await reserve(client)

    refused = call(off, ioc=False)
    assert refused.status_code == 403 and refused.json()["code"] == "ioc_off"


def test_completing_a_lookup_keeps_or_gives_it_back():
    async def scenario(client, ctx):
        answered = (await reserve(client)).json()["lookup_id"]
        unanswered = (await reserve(client, value="evil.example")).json()["lookup_id"]
        a = await client.post(f"{METER}/{answered}/complete", json={"answered": True}, headers=as_user("talon-analyst"))
        b = await client.post(f"{METER}/{unanswered}/complete", json={"answered": False}, headers=as_user("talon-analyst"))
        again = await client.post(f"{METER}/{answered}/complete", json={"answered": False}, headers=as_user("talon-analyst"))
        bad = await client.post(f"{METER}/{answered}/complete", json={"answered": "yes"}, headers=as_user("talon-analyst"))
        return a, b, again, bad, await rows(ctx.db, CustomerPortalIocLookup), answered

    a, b, again, bad, stored, answered = call(scenario)
    assert (a.status_code, b.status_code) == (204, 204)
    assert again.status_code == 404  # a completed lookup is never touched again
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_request"
    (row,) = stored
    assert row.id == answered and row.completed_at is not None


# ── the review proxy ──────────────────────────────────────────────────────────

REVIEW = "/talon/v2/portal_review/threads"
A_THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"


def test_the_review_rule():
    talon = FakeTalon()

    async def scenario(client, ctx):
        answers = {}
        for user in ("admin", "ana", "resp", "gus"):
            answers[user] = await client.get(REVIEW, params={"customer_code": ACME}, headers=as_user(user))
        answers["portal"] = await client.get(REVIEW, params={"customer_code": ACME}, headers=as_user("jane"))
        answers["no_customer"] = await client.get(REVIEW, headers=as_user("admin"))
        answers["messages"] = await client.get(f"{REVIEW}/{A_THREAD}/messages", headers=as_user("ana"))
        forwarded = [
            (r.url.path, r.headers["X-Talon-Role"], r.url.params.get("customer_code")) for r in talon.requests if "review" in r.url.path
        ]
        return answers, forwarded

    answers, forwarded = call(scenario, talon=talon)
    assert (answers["admin"].status_code, answers["ana"].status_code, answers["resp"].status_code) == (200, 200, 200)
    assert answers["gus"].status_code == 403 and answers["gus"].json()["code"] == "review_forbidden"
    assert answers["portal"].status_code == 403
    assert answers["no_customer"].status_code == 422 and answers["no_customer"].json()["code"] == "invalid_request"
    assert answers["messages"].status_code == 200
    assert forwarded == [
        ("/v2/portal-review/threads", "admin", ACME),
        ("/v2/portal-review/threads", "analyst", ACME),
        ("/v2/portal-review/threads", "responder", ACME),
        (f"/v2/portal-review/threads/{A_THREAD}/messages", "analyst", None),
    ]


def test_a_reviewer_needs_unrestricted_tag_access():
    talon = FakeTalon()

    async def scenario(client, ctx):
        async with ctx.db.session() as s:
            tag = AlertTag(tag="restricted")
            s.add_all([tag, TagAccessSettings(enabled=True, untagged_alert_behavior="visible_to_all")])
            await s.commit()
            s.add(UserTagAccess(user_id=2, tag_id=tag.id))
            await s.commit()
        listed = await client.get(REVIEW, params={"customer_code": ACME}, headers=as_user("ana"))
        transcript = await client.get(f"{REVIEW}/{A_THREAD}/messages", headers=as_user("ana"))
        admin = await client.get(REVIEW, params={"customer_code": ACME}, headers=as_user("admin"))
        return listed, transcript, admin, [r for r in talon.requests if "review" in r.url.path]

    listed, transcript, admin, forwarded = call(scenario, talon=talon)
    assert listed.status_code == 403 and listed.json()["code"] == "review_forbidden"
    assert transcript.status_code == 404 and transcript.json()["code"] == "thread_not_found"
    assert admin.status_code == 200 and len(forwarded) == 1


def test_the_review_and_meter_routes_are_behind_the_talon_v2_setting():
    async def scenario(client, ctx):
        review = await client.get(REVIEW, params={"customer_code": ACME}, headers=as_user("admin"))
        meter = await reserve(client)
        return review, meter

    review, meter = call(scenario, v2=False)
    assert review.status_code == 404 and meter.status_code == 404


# ── the portal identity builder ───────────────────────────────────────────────


def test_the_portal_identity_is_for_portal_users_with_a_customer_only():
    from types import SimpleNamespace

    from app.connectors.talon.services.identity import PortalIdentityRefused
    from app.connectors.talon.services.identity import portal_identity_headers
    from app.connectors.talon.services.identity import talon_identity_headers

    async def scenario(client, ctx):
        outcomes = {}
        async with ctx.db.session() as session:
            for name, user in (
                ("analyst", SimpleNamespace(id=2, username="ana", role_id=2)),
                ("admin", SimpleNamespace(id=1, username="admin", role_id=1)),
                ("orphan", SimpleNamespace(id=77, username="nobody", role_id=4)),
            ):
                try:
                    await portal_identity_headers(user, session)
                except PortalIdentityRefused as e:
                    outcomes[name] = e.code
            try:
                await talon_identity_headers(SimpleNamespace(id=10, username="jane", role_id=4), session)
            except Exception as e:  # noqa: BLE001
                outcomes["soc_builder"] = getattr(e, "status_code", None)
            headers = await portal_identity_headers(SimpleNamespace(id=11, username="rory", role_id=4), session)
        return outcomes, headers

    outcomes, headers = call(scenario)
    assert outcomes == {"analyst": "not_portal_role", "admin": "not_portal_role", "orphan": "customer_not_accessible", "soc_builder": 403}
    assert headers["X-Talon-Read-Only"] == ACME and headers["X-Talon-Customers"] == ACME
    upstream = v2_client.build_upstream_headers("k", headers, accept="application/json", json_body=False)
    assert {k for k in upstream if k.startswith("X-Talon-")} == set(PORTAL_IDENTITY_HEADERS)
    with pytest.raises(ValueError):
        v2_client.build_upstream_headers("k", {**headers, "X-Talon-Extra": "1"}, accept="application/json", json_body=False)


def test_the_read_back_forwards_only_the_callers_paging():
    talon = FakeTalon()

    async def scenario(client, ctx):
        thread_id = talon.add_thread()
        await send(client, "GET", f"{BASE}/threads/{thread_id}/messages", None)
        await client.get(f"{BASE}/threads/{thread_id}/messages", params={"limit": 5, "before": "c1", "x": "y"}, headers=as_user("jane"))
        return [dict(r.url.params) for r in talon.requests if r.url.path.endswith("/messages")]

    assert call(scenario, talon=talon) == [{}, {"limit": "5", "before": "c1"}]


# ── review fixes (#1327) ──────────────────────────────────────────────────────


def test_a_draft_is_filed_only_on_its_own_customers_target():
    """M1: a user of ACME and GLOBEX can't get an ACME draft filed on a GLOBEX alert or case."""
    talon = FakeTalon()

    async def scenario(client, ctx):
        await set_chat(ctx.db, GLOBEX, portal_chat_enabled=False)
        async with ctx.db.session() as s:  # multi may write on GLOBEX for this test
            await s.execute(UserCustomerAccess.__table__.update().values(read_only=False))
            await s.commit()
        draft_id = talon.add_draft("alert", ctx.ids.globex_alert, customer_code=ACME, owner="12")
        response = await submit(client, draft_id, user="multi")
        return draft_id, response, await rows(ctx.db, CustomerPortalSocRequest)

    draft_id, response, filed = call(scenario, talon=talon)
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert filed == []
    assert talon.outcomes == [(draft_id, {"outcome": "failed", "failure": "not_found"})]


def test_an_orphan_that_gets_its_comment_meanwhile_is_kept_and_reported():
    """L1: the orphan delete is conditional; a row whose comment was written in between stays."""
    from sqlalchemy import update
    from sqlalchemy.sql.dml import Delete

    from app.customer_portal.services import talon_chat_drafts

    async def scenario(client, ctx):
        draft_id = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"
        async with ctx.db.session() as s:
            row = CustomerPortalSocRequest(
                customer_code=ACME,
                question=QUESTION,
                status="open",
                requested_by="jane",
                requested_at=a_while_ago(6),
                talon_draft_id=draft_id,
            )
            s.add(row)
            await s.commit()
            row_id = row.id
        async with ctx.db.session() as session:
            real = session.execute

            async def racing(statement, *args, **kwargs):
                if isinstance(statement, Delete):  # the filing writes its comment just before the delete
                    await real(update(CustomerPortalSocRequest).where(CustomerPortalSocRequest.id == row_id).values(comment_id=7))
                    await session.commit()
                return await real(statement, *args, **kwargs)

            session.execute = racing
            found = await talon_chat_drafts.look(draft_id, ACME, session)
        return row_id, found, await rows(ctx.db, CustomerPortalSocRequest)

    row_id, found, stored = call(scenario)
    assert found == row_id
    assert [r.id for r in stored] == [row_id]


def test_a_unique_key_conflict_without_a_comment_is_a_conflict_and_posts_no_outcome(monkeypatch):
    """L2: the other request hasn't finished: it reports the draft, not this one."""
    from app.customer_portal.services import soc_requests

    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("case", ctx.ids.open_case)
        real = soc_requests._reserve

        async def racing(*args, **kwargs):
            async with ctx.db.session() as s:
                s.add(
                    CustomerPortalSocRequest(
                        customer_code=ACME,
                        question="theirs",
                        status="open",
                        requested_by="jane",
                        requested_at=a_while_ago(0),
                        talon_draft_id=draft_id,
                    ),
                )
                await s.commit()
            return await real(*args, **kwargs)

        monkeypatch.setattr(soc_requests, "_reserve", racing)
        return await submit(client, draft_id)

    response = call(scenario, talon=talon)
    assert response.status_code == 409 and response.json()["code"] == "draft_conflict"
    assert talon.outcomes == []


def test_a_filed_draft_is_reported_even_while_the_switch_is_off():
    """L3: the lookup-only pass records a filing that already happened; it files nothing new."""
    talon = FakeTalon()

    async def scenario(client, ctx):
        filed_id = talon.add_draft("alert", ctx.ids.linked)
        unfiled_id = talon.add_draft("alert", ctx.ids.lonely)
        first = await submit(client, filed_id)
        talon.outcomes.clear()
        await set_chat(ctx.db, portal_chat_enabled=False)
        again = await submit(client, filed_id)
        other_user = await submit(client, filed_id, user="rory")
        unfiled = await submit(client, unfiled_id)
        return filed_id, first, again, other_user, unfiled, await rows(ctx.db, CustomerPortalSocRequest)

    filed_id, first, again, other_user, unfiled, filed = call(scenario, talon=talon)
    assert first.status_code == 200 and again.status_code == 200 and again.json() == first.json()
    assert other_user.status_code == 403 and other_user.json()["code"] == "portal_off"  # not theirs: no lookup answer
    assert unfiled.status_code == 403 and unfiled.json()["code"] == "portal_off"
    assert len(filed) == 1
    assert talon.outcomes == [(filed_id, {"outcome": "submitted", "copilot_ref": str(filed[0].id)})]


def test_two_simultaneous_submits_of_one_draft_file_it_once():
    talon = FakeTalon()

    async def scenario(client, ctx):
        draft_id = talon.add_draft("alert", ctx.ids.linked)
        answers = await asyncio.gather(submit(client, draft_id), submit(client, draft_id))
        return answers, await rows(ctx.db, CustomerPortalSocRequest)

    answers, filed = call(scenario, talon=talon)
    (row,) = filed
    assert {r.status_code for r in answers} <= {200, 409} and any(r.status_code == 200 for r in answers)
    for response in answers:
        assert response.json() == {"request_id": row.id} if response.status_code == 200 else response.json()["code"] == "draft_conflict"
    assert {body["outcome"] for _, body in talon.outcomes} == {"submitted"}
    assert {body["copilot_ref"] for _, body in talon.outcomes} == {str(row.id)}


def test_the_meter_refuses_a_disabled_portal_user():
    async def scenario(client, ctx):
        async with ctx.db.session() as s:
            await s.execute(User.__table__.update().where(User.id == 10).values(disabled_at=a_while_ago(1)))
            await s.commit()
        return await reserve(client), await rows(ctx.db, CustomerPortalIocLookup)

    response, stored = call(scenario)
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert stored == []


def test_the_meter_completes_only_its_own_open_lookups():
    """L4: a lookup the portal itself reserved is never completed or deleted by the meter."""
    from app.customer_portal.services import ioc_enrichment

    async def scenario(client, ctx):
        async with ctx.db.session() as s:
            portal_own = await ioc_enrichment.reserve_lookup(ACME, "f" * 64, s, user_id=10)
        meters = (await reserve(client)).json()["lookup_id"]
        refused = await client.post(f"{METER}/{portal_own}/complete", json={"answered": False}, headers=as_user("talon-analyst"))
        done = await client.post(f"{METER}/{meters}/complete", json={"answered": True}, headers=as_user("talon-analyst"))
        stored = {row.id: row for row in await rows(ctx.db, CustomerPortalIocLookup)}
        return portal_own, meters, refused, done, stored

    portal_own, meters, refused, done, stored = call(scenario)
    assert refused.status_code == 404 and refused.json()["code"] == "not_found"
    assert done.status_code == 204
    assert stored[portal_own].completed_at is None and stored[portal_own].reserved_by is None
    assert stored[meters].completed_at is not None and stored[meters].reserved_by == "talon"
