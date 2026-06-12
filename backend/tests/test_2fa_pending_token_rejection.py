"""Regression tests for GHSA-5m69-7h2p-6qfw — 2FA bypass via token refresh.

A "2fa_pending" token is issued by POST /auth/token when the account has 2FA
enabled, but the second factor has NOT been completed. It is signed with the
same JWT_SECRET as a real session token, so the decode chokepoint must reject
it everywhere a session token is expected (e.g. /auth/refresh,
/auth/me/customers). Only POST /auth/2fa/validate (via _decode_temp_token) may
consume it.

These are pure unit tests against the decode layer — no DB or app wiring.

Run with: cd backend && python -m pytest tests/test_2fa_pending_token_rejection.py
"""

import os

# AuthHandler loads JWT_SECRET at class-definition time, so it must be set
# before importing the module under test.
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.auth.routes.totp import _create_temp_token  # noqa: E402
from app.auth.routes.totp import _decode_temp_token  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402

auth_handler = AuthHandler()


def test_2fa_pending_token_is_rejected_by_decode_token():
    temp_token = _create_temp_token("admin")
    username, scopes = auth_handler.decode_token(temp_token)
    # Must surface the dedicated sentinel, never the real subject/scopes.
    assert username == "2FA pending"
    assert scopes == []


def test_full_session_token_still_decodes_normally():
    # A normal session token carries scopes and no 2fa_pending type.
    import jwt

    payload = {"sub": "admin", "scopes": ["admin"]}
    token = jwt.encode(payload, auth_handler.secret, algorithm="HS256")
    username, scopes = auth_handler.decode_token(token)
    assert username == "admin"
    assert scopes == ["admin"]


def test_2fa_validate_path_still_accepts_pending_token():
    # The intended consumer must keep working — otherwise 2FA login is broken.
    temp_token = _create_temp_token("admin")
    assert _decode_temp_token(temp_token) == "admin"
