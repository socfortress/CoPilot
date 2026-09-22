"""``GET /auth/refresh`` must re-issue a customer_user token with its ``customer_codes`` claim.

The Customer Portal reads that claim to populate its customer filter. Login and 2FA
completion attach it; before this test existed the refresh route did not, so a
refreshed portal session silently lost every customer the moment the frontend
re-parsed the token.

Pure unit test: the DB lookups behind the route are patched, no app wiring.

Run with: cd backend && python -m pytest tests/test_auth_refresh_customer_codes.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import jwt  # noqa: E402

from app.auth.models.users import RoleEnum  # noqa: E402
from app.auth.routes import auth as auth_routes  # noqa: E402


def _refresh_for(role_id: int, codes):
    user = SimpleNamespace(id=42, username="portal-user", role_id=role_id)
    with (
        patch.object(auth_routes, "get_customer_codes_for_user", AsyncMock(return_value=codes)) as lookup,
        patch("app.auth.utils.get_role", AsyncMock(return_value=RoleEnum(role_id).name)),
    ):
        token = asyncio.run(auth_routes.refresh_token(current_user=user))["access_token"]
    return jwt.decode(token, auth_routes.auth_handler.secret, algorithms=["HS256"]), lookup


def test_refresh_reattaches_customer_codes_for_customer_user():
    payload, lookup = _refresh_for(RoleEnum.customer_user.value, ["ACME", "GLOBEX"])
    assert payload["customer_codes"] == ["ACME", "GLOBEX"]
    assert payload["sub"] == "portal-user"
    lookup.assert_awaited_once_with(42)


def test_refresh_leaves_analyst_token_without_the_claim():
    payload, lookup = _refresh_for(RoleEnum.analyst.value, ["ACME"])
    assert "customer_codes" not in payload
    lookup.assert_not_awaited()
