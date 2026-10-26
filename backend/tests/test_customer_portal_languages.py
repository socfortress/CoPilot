"""The Customer Portal's languages (#1310).

Real routers, a real in-memory database; only token decoding, user lookup and the audit writer
are replaced.

Pinned here:
- a customer has English only until an admin enables more; English can't be removed and an
  unknown code is refused; an analyst reads the setting, only an admin writes it; a change is
  audited with old and new languages, a save that changes nothing is not;
- a portal user may pick English or any language enabled for at least one of their customers
  (the union); a language enabled for no customer of theirs is refused;
- the pick is stored on the account and shown by ``/me``; once its language is disabled the portal
  shows English, and re-enabling it brings the pick back;
- the pure rules (order, English first, effective locale).

Run with: cd backend && python -m pytest tests/test_customer_portal_languages.py
"""

import asyncio
import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services import languages as service  # noqa: E402
from app.customer_portal.utils.locales import SUPPORTED_LOCALES  # noqa: E402
from app.customer_portal.utils.locales import check_languages  # noqa: E402
from app.customer_portal.utils.locales import effective_locale  # noqa: E402
from app.customer_portal.utils.locales import ordered  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalLanguageSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402

# id, username, role: admin, analyst, and portal users of one customer, of two, and of none.
PEOPLE = [(1, "admin", 1), (2, "ana", 2), (10, "jane", 4), (11, "multi", 4), (12, "loner", 4)]
SCOPES = {name: ["customer_user"] if role == 4 else (["admin"] if role == 1 else ["analyst"]) for _, name, role in PEOPLE}
BASE = "/customer_portal/languages"


class Recorded(SimpleNamespace):
    pass


def _app(factory) -> FastAPI:
    from app.routers import customer_portal

    app = FastAPI()
    app.include_router(customer_portal.router)

    async def _session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(factory, languages: dict) -> None:
    async with factory() as s:
        s.add_all(User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE)
        s.add_all(Customers(customer_code=code, customer_name=code.title()) for code in ("ACME", "GLOBEX"))
        await s.commit()
        s.add_all(
            [
                UserCustomerAccess(user_id=2, customer_code="ACME"),
                UserCustomerAccess(user_id=10, customer_code="ACME"),
                UserCustomerAccess(user_id=11, customer_code="ACME"),
                UserCustomerAccess(user_id=11, customer_code="GLOBEX"),
            ],
        )
        s.add_all(CustomerPortalLanguageSettings(customer_code=code, languages=langs) for code, langs in languages.items())
        await s.commit()


def call(scenario, languages=None):
    async def _inner():
        engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        tables = _tables() + [SQLModel.metadata.tables["customer_portal_language_settings"]]
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        await _seed(factory, languages or {})
        rec = Recorded(audit=AsyncMock(), factory=factory)

        async def resolve_user(self, request, username):
            # Read live, like the real lookup, so a stored pick shows on the next request.
            async with factory() as s:
                return (await s.execute(User.__table__.select().where(User.username == username))).first()

        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
            AuthHandler,
            "_resolve_user",
            resolve_user,
        ), patch("app.customer_portal.routes.languages.record_audit_event", rec.audit):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(factory)), base_url="http://test") as client:
                return await scenario(client, rec)

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


# ── the pure rules ────────────────────────────────────────────────────────────


def test_languages_are_ordered_with_english_first_and_always_there():
    assert ordered(["es", "it", "es", "xx"]) == ["en", "it", "es"]
    assert ordered([]) == ["en"]
    assert SUPPORTED_LOCALES[0] == "en"


def test_an_admins_list_must_keep_english_and_name_only_known_languages():
    assert check_languages(["it", "en"]) == ["en", "it"]
    with pytest.raises(ValueError, match="English"):
        check_languages(["it"])
    with pytest.raises(ValueError, match="Unknown language: jp"):
        check_languages(["en", "jp"])


def test_the_portal_shows_the_pick_only_while_it_is_available():
    assert effective_locale("it", ["en", "it"]) == "it"
    assert effective_locale("it", ["en"]) == "en"
    assert effective_locale(None, ["en", "it"]) == "en"


# ── the customer's setting ───────────────────────────────────────────────────


def test_a_customer_has_english_only_until_an_admin_enables_more():
    async def scenario(client, rec):
        before = (await client.get(f"{BASE}/settings/ACME", headers=as_user("ana"))).json()
        saved = await client.put(f"{BASE}/settings/ACME", json={"languages": ["it", "en", "cs"]}, headers=as_user("admin"))
        after = (await client.get(f"{BASE}/settings/ACME", headers=as_user("ana"))).json()
        return before, saved, after, rec

    before, saved, after, rec = call(scenario)
    assert before["settings"]["languages"] == ["en"]
    assert before["supported"] == list(SUPPORTED_LOCALES)
    assert saved.status_code == 200 and saved.json()["settings"]["languages"] == ["en", "it", "cs"]
    assert after["settings"]["languages"] == ["en", "it", "cs"]
    assert after["settings"]["updated_by"] == 1
    audit = rec.audit.await_args.kwargs
    assert audit["action"].value == "portal_languages.settings_update"
    assert audit["old_value"] == {"languages": ["en"]} and audit["new_value"] == {"languages": ["en", "it", "cs"]}
    assert audit["customer_code"] == "ACME"


def test_a_save_that_changes_nothing_is_not_audited():
    async def scenario(client, rec):
        return await client.put(f"{BASE}/settings/ACME", json={"languages": ["en", "it"]}, headers=as_user("admin")), rec

    res, rec = call(scenario, languages={"ACME": ["en", "it"]})
    assert res.status_code == 200
    rec.audit.assert_not_awaited()


def test_english_cant_be_removed_and_an_unknown_language_is_refused():
    async def scenario(client, rec):
        no_english = await client.put(f"{BASE}/settings/ACME", json={"languages": ["it"]}, headers=as_user("admin"))
        unknown = await client.put(f"{BASE}/settings/ACME", json={"languages": ["en", "jp"]}, headers=as_user("admin"))
        stored = (await client.get(f"{BASE}/settings/ACME", headers=as_user("admin"))).json()
        return no_english, unknown, stored

    no_english, unknown, stored = call(scenario)
    assert no_english.status_code == 422 and "English" in no_english.text
    assert unknown.status_code == 422 and "jp" in unknown.text
    assert stored["settings"]["languages"] == ["en"]


def test_only_an_admin_writes_it_and_an_unknown_customer_is_not_found():
    async def scenario(client, rec):
        by_analyst = await client.put(f"{BASE}/settings/ACME", json={"languages": ["en", "it"]}, headers=as_user("ana"))
        by_portal = await client.put(f"{BASE}/settings/ACME", json={"languages": ["en", "it"]}, headers=as_user("jane"))
        read_by_portal = await client.get(f"{BASE}/settings/ACME", headers=as_user("jane"))
        unknown = await client.put(f"{BASE}/settings/NOPE", json={"languages": ["en"]}, headers=as_user("admin"))
        other_customer = await client.get(f"{BASE}/settings/GLOBEX", headers=as_user("ana"))
        return by_analyst, by_portal, read_by_portal, unknown, other_customer

    by_analyst, by_portal, read_by_portal, unknown, other_customer = call(scenario)
    assert by_analyst.status_code == 403 and by_portal.status_code == 403 and read_by_portal.status_code == 403
    assert unknown.status_code == 404
    assert other_customer.status_code == 403


# ── the portal user's pick ───────────────────────────────────────────────────


def test_a_portal_user_picks_from_the_union_of_their_customers_languages():
    async def scenario(client, rec):
        jane = (await client.get(BASE, headers=as_user("jane"))).json()
        multi = (await client.get(BASE, headers=as_user("multi"))).json()
        loner = (await client.get(BASE, headers=as_user("loner"))).json()
        return jane, multi, loner

    jane, multi, loner = call(scenario, languages={"ACME": ["en", "it"], "GLOBEX": ["en", "de", "nl"]})
    assert jane["available"] == ["en", "it"] and jane["locale"] == "en"
    assert multi["available"] == ["en", "it", "de", "nl"]
    # No customer at all: English only.
    assert loner["available"] == ["en"]


def test_the_pick_is_stored_on_the_account_and_shown_by_me():
    async def scenario(client, rec):
        saved = await client.put(f"{BASE}/me", json={"locale": "it"}, headers=as_user("jane"))
        me = (await client.get("/customer_portal/me", headers=as_user("jane"))).json()
        again = (await client.get(BASE, headers=as_user("jane"))).json()
        async with rec.factory() as s:
            stored = (await s.get(User, 10)).locale
        return saved, me, again, stored

    saved, me, again, stored = call(scenario, languages={"ACME": ["en", "it"]})
    assert saved.status_code == 200 and saved.json()["locale"] == "it"
    assert me["locale"] == "it" and me["available_locales"] == ["en", "it"]
    assert me["locale_chosen"] is True
    assert again["locale"] == "it"
    assert stored == "it"


def test_a_language_enabled_for_none_of_their_customers_is_refused():
    async def scenario(client, rec):
        not_enabled = await client.put(f"{BASE}/me", json={"locale": "de"}, headers=as_user("jane"))
        unknown = await client.put(f"{BASE}/me", json={"locale": "jp"}, headers=as_user("jane"))
        english = await client.put(f"{BASE}/me", json={"locale": "en"}, headers=as_user("loner"))
        by_analyst = await client.put(f"{BASE}/me", json={"locale": "it"}, headers=as_user("ana"))
        return not_enabled, unknown, english, by_analyst

    not_enabled, unknown, english, by_analyst = call(scenario, languages={"ACME": ["en", "it"], "GLOBEX": ["en", "de"]})
    assert not_enabled.status_code == 400 and not_enabled.json()["detail"] == service.NOT_AVAILABLE
    assert unknown.status_code == 400
    # English is always there, even with no customer.
    assert english.status_code == 200
    assert by_analyst.status_code == 403


def test_a_disabled_language_falls_back_to_english_and_comes_back_when_re_enabled():
    async def scenario(client, rec):
        await client.put(f"{BASE}/me", json={"locale": "it"}, headers=as_user("jane"))
        await client.put(f"{BASE}/settings/ACME", json={"languages": ["en"]}, headers=as_user("admin"))
        off = (await client.get("/customer_portal/me", headers=as_user("jane"))).json()
        await client.put(f"{BASE}/settings/ACME", json={"languages": ["en", "it"]}, headers=as_user("admin"))
        back = (await client.get("/customer_portal/me", headers=as_user("jane"))).json()
        return off, back

    off, back = call(scenario, languages={"ACME": ["en", "it"]})
    assert off["locale"] == "en" and off["available_locales"] == ["en"]
    assert back["locale"] == "it"


def test_a_stored_list_without_english_still_reads_with_english():
    async def scenario(client, rec):
        return (await client.get(f"{BASE}/settings/ACME", headers=as_user("admin"))).json()

    # Written by hand in the database: English is put back when it is read.
    res = call(scenario, languages={"ACME": ["it"]})
    assert res["settings"]["languages"] == ["en", "it"]


# --- the three apps name the same languages ---------------------------------------------------


def _ts_codes(path, constant):
    """The string codes of ``constant = [ ... ] as const`` in a TypeScript file."""
    source = (Path(__file__).resolve().parents[2] / path).read_text()
    match = re.search(rf"{constant}\s*=\s*\[([^\]]*)\]\s*as const", source)
    assert match, f"{constant} not found in {path}"
    return tuple(re.findall(r'"([a-z]{2})"', match.group(1)))


def test_the_portal_and_the_frontend_list_the_backends_languages_in_its_order():
    # The portal's picker, CoPilot's Portal Languages tab and the API must agree, English first.
    assert _ts_codes("customer-portal/src/lang/config.ts", "SUPPORTED_LOCALES") == SUPPORTED_LOCALES
    assert _ts_codes("frontend/src/components/customerPortal/portalLanguages.ts", "PORTAL_LANGUAGES") == SUPPORTED_LOCALES
    assert SUPPORTED_LOCALES[0] == "en"


def test_the_portal_ships_messages_for_every_language():
    locales = Path(__file__).resolve().parents[2] / "customer-portal" / "src" / "lang" / "locales"
    shipped = {p.name for p in locales.iterdir() if p.is_dir()}
    assert shipped == set(SUPPORTED_LOCALES)
