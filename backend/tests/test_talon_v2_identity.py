"""The five identity headers CoPilot sends talon-analyst on every v2 request (plan M5-5a).

``talon_identity_headers(user, session)`` against a real in-memory database (users, customer
assignments, tag RBAC), for an admin, an assigned analyst, an unassigned analyst, a responder,
tag RBAC on with each untagged behaviour, and a customer code outside talon-analyst's grammar.
Every value is also held to talon-analyst's own header rules (``talon/api/identity.py``,
``talon/tenancy/access.py``), so a header CoPilot builds is one talon-analyst accepts.

No network. Run with: cd backend && python -m pytest tests/test_talon_v2_identity.py
"""

import asyncio
import os
import re
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.auth.models.users import RoleTagAccess  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.models.users import UserTagAccess  # noqa: E402
from app.connectors.talon.services import identity  # noqa: E402
from app.connectors.talon.services.identity import customers_header  # noqa: E402
from app.connectors.talon.services.identity import is_talon_customer_code  # noqa: E402
from app.connectors.talon.services.identity import tags_header  # noqa: E402
from app.connectors.talon.services.identity import talon_identity_headers  # noqa: E402
from app.connectors.talon.services.identity import talon_role  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import TagAccessSettings  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402

ADMIN = SimpleNamespace(id=1, username="admin", role_id=1)
ANA = SimpleNamespace(id=2, username="ana", role_id=2)
LONELY = SimpleNamespace(id=3, username="lonely", role_id=2)
RESP = SimpleNamespace(id=5, username="resp", role_id=5)
MESSY = SimpleNamespace(id=6, username="messy", role_id=2)
PORTAL = SimpleNamespace(id=7, username="portal", role_id=4)
SCHEDULER = SimpleNamespace(id=8, username="scheduler", role_id=3)

BAD_CODES = ["has space", "-leading-dash", "a/b", "café", " ACME"]

# talon-analyst's rules for each header, as it parses them.
USER_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,48}")
CODE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def assert_talon_accepts(headers):
    assert list(headers) == ["X-Talon-User", "X-Talon-Role", "X-Talon-Customers", "X-Talon-Tags", "X-Talon-Untagged"]
    assert USER_ID_RE.fullmatch(headers["X-Talon-User"])
    assert headers["X-Talon-Role"] in ("admin", "analyst", "responder")
    customers = headers["X-Talon-Customers"]
    if customers == "*":
        assert headers["X-Talon-Role"] == "admin"
    elif customers:
        assert all(CODE_RE.fullmatch(code) for code in customers.split(","))
    tags = headers["X-Talon-Tags"]
    if tags not in ("*", ""):
        assert all(t.isdigit() and 1 <= int(t) <= 2_147_483_647 for t in tags.split(","))
    assert headers["X-Talon-Untagged"] in ("true", "false")


async def _seed(db, *, rbac=None, untagged="visible_to_all", default_tag=None):
    async with db.session() as session:
        session.add_all(
            [
                User(id=u.id, username=u.username, password="x" * 8, email=f"{u.username}@example.com", role_id=u.role_id)
                for u in (ADMIN, ANA, LONELY, RESP, MESSY)
            ]
            + [Customers(customer_code=code, customer_name=code[:50]) for code in ["ACME", "GLOBEX", *BAD_CODES]]
            + [AlertTag(id=n, tag=f"tag-{n}") for n in (1, 2, 3, 4)],
        )
        await session.commit()
        session.add_all(
            [
                UserCustomerAccess(user_id=ANA.id, customer_code="GLOBEX"),
                UserCustomerAccess(user_id=ANA.id, customer_code="ACME"),
                UserCustomerAccess(user_id=RESP.id, customer_code="ACME"),
                UserCustomerAccess(user_id=MESSY.id, customer_code="ACME"),
            ]
            + [UserCustomerAccess(user_id=MESSY.id, customer_code=code) for code in BAD_CODES],
        )
        if rbac is not None:
            session.add(TagAccessSettings(id=1, enabled=rbac, untagged_alert_behavior=untagged, default_tag_id=default_tag))
            session.add_all(
                [
                    UserTagAccess(user_id=ANA.id, tag_id=3),
                    RoleTagAccess(role_id=2, tag_id=1),  # the analyst role: also a responder's (ROLE_EXTENDS)
                ],
            )
        await session.commit()


def headers_for(user, **seed):
    async def run():
        db = await Db().create()
        try:
            await _seed(db, **seed)
            async with db.session() as session:
                return await talon_identity_headers(user, session)
        finally:
            await db.dispose()

    headers = asyncio.run(run())
    assert_talon_accepts(headers)
    return headers


# ── who the user is ───────────────────────────────────────────────────────────


def test_an_admin_has_every_customer_and_tag():
    assert headers_for(ADMIN) == {
        "X-Talon-User": "1",
        "X-Talon-Role": "admin",
        "X-Talon-Customers": "*",
        "X-Talon-Tags": "*",
        "X-Talon-Untagged": "true",
    }


def test_an_assigned_analyst_has_their_customers_sorted():
    headers = headers_for(ANA)
    assert headers["X-Talon-User"] == "2"
    assert headers["X-Talon-Role"] == "analyst"
    assert headers["X-Talon-Customers"] == "ACME,GLOBEX"
    # Tag RBAC off (no settings row): every tag, untagged included.
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("*", "true")


def test_an_unassigned_analyst_has_no_customer():
    assert headers_for(LONELY)["X-Talon-Customers"] == ""


def test_a_responder_is_one_role_not_the_tokens_two_scopes():
    headers = headers_for(RESP)
    assert headers["X-Talon-Role"] == "responder"
    assert headers["X-Talon-Customers"] == "ACME"


def test_roles_that_may_not_chat_are_refused_before_anything_is_sent():
    for user in (PORTAL, SCHEDULER, SimpleNamespace(id=9, username="ghost", role_id=99)):
        with pytest.raises(HTTPException) as refused:
            talon_role(user)
        assert refused.value.status_code == 403


# ── tags ──────────────────────────────────────────────────────────────────────


def test_tag_rbac_off_in_its_settings_row_is_every_tag():
    headers = headers_for(ANA, rbac=False, untagged="admin_only")
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("*", "true")


def test_tag_rbac_on_visible_to_all():
    headers = headers_for(ANA, rbac=True, untagged="visible_to_all")
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("1,3", "true")


def test_tag_rbac_on_admin_only():
    headers = headers_for(ANA, rbac=True, untagged="admin_only")
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("1,3", "false")


def test_tag_rbac_on_default_tag_the_user_has():
    headers = headers_for(ANA, rbac=True, untagged="default_tag", default_tag=3)
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("1,3", "true")


def test_tag_rbac_on_default_tag_the_user_lacks():
    headers = headers_for(ANA, rbac=True, untagged="default_tag", default_tag=4)
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("1,3", "false")


def test_tag_rbac_on_a_responder_gets_the_analyst_roles_tags():
    headers = headers_for(RESP, rbac=True, untagged="admin_only")
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("1", "false")


def test_tag_rbac_on_an_analyst_without_tags_sees_none():
    headers = headers_for(LONELY, rbac=True, untagged="admin_only")
    # LONELY has no user tags, but the analyst role's tag 1 applies to every analyst.
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("1", "false")


def test_tag_rbac_on_an_admin_is_unrestricted():
    headers = headers_for(ADMIN, rbac=True, untagged="admin_only")
    assert (headers["X-Talon-Tags"], headers["X-Talon-Untagged"]) == ("*", "true")


def test_tags_header_values():
    assert tags_header({"*"}) == "*"
    assert tags_header({"*", 4}) == "*"
    assert tags_header(set()) == ""
    assert tags_header({12, 3, 7}) == "3,7,12"
    # Nothing talon-analyst can't read: it would 400 every request. Dropping narrows the filter.
    assert tags_header({3, 0, -1, 2**31, "7", True}) == "3"


# ── customer codes ────────────────────────────────────────────────────────────


def test_a_code_outside_talon_analysts_grammar_is_dropped_and_logged():
    with patch.object(identity.logger, "warning") as warned:
        headers = headers_for(MESSY)
    assert headers["X-Talon-Customers"] == "ACME"
    (message,), _ = warned.call_args
    assert f"dropped {len(BAD_CODES)} customer code(s)" in message and "user 6" in message


def test_the_grammar_is_talon_analysts():
    assert is_talon_customer_code("ACME")
    assert is_talon_customer_code("lab.canary_2-x")
    assert is_talon_customer_code("a" * 64)
    for bad in ["", "a" * 65, "-x", ".x", "_x", "x y", "x,y", "*", "x\n", "talon chat memory", "ACME ", 7, None]:
        assert not is_talon_customer_code(bad), bad


def test_only_an_admin_may_be_sent_the_wildcard():
    user = SimpleNamespace(id=2, username="ana", role_id=2)
    assert customers_header(user, "admin", ["*"]) == "*"
    # A non-admin with "*" can't happen today; if it ever did, it would mean nothing, never all.
    assert customers_header(user, "analyst", ["*"]) == ""
    assert customers_header(user, "analyst", ["*", "ACME", "ACME"]) == "ACME"
