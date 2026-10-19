"""A password an admin chose must be replaced by the user (#1277).

An admin sets ``user.must_change_password`` by emailing a temporary password, resetting a
password or creating an account; the user's own change clears it. While it is set, a
``customer_user`` reaches only ``ALLOWED_PATHS``: every other authenticated route answers
403 with ``X-Password-Change-Required`` (never 401, which the portal reads as the session
ending). This file pins the decision, where it runs, the admin routes that set the flag
and the change that clears it; tests/e2e/password_change_e2e.py runs it on MySQL.

Run with: cd backend && python -m pytest tests/test_password_change.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "unit-test-secret-not-the-default")

from fastapi import HTTPException  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.security import OAuth2PasswordBearer  # noqa: E402
from fastapi.security import SecurityScopes  # noqa: E402

from app.audit.models.audit import AuditAction  # noqa: E402
from app.auth.models.users import PasswordReset  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402
from app.auth.services import password_change  # noqa: E402
from app.auth.services import security_admin  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402

NEW_PASSWORD = "Fresh-Start-2026!"
TEMP_PASSWORD = "Temp-Issued-2026!"


def _user(role=RoleEnum.customer_user, held=True, user_id=11, username="portal1"):
    return SimpleNamespace(id=user_id, username=username, role_id=role.value, must_change_password=held, password="hash")


def _request(path):
    return SimpleNamespace(scope={"route": SimpleNamespace(path=path)}, url=SimpleNamespace(path=path), state=SimpleNamespace())


def _routes():
    import copilot

    return [route for route in copilot.app.routes if isinstance(route, APIRoute)]


class TestDecision:
    def test_a_held_customer_reaches_only_the_change_and_what_it_needs(self):
        user = _user()
        for path in password_change.ALLOWED_PATHS:
            # As the app mounts them (under /api) and as a test app may (without).
            password_change.enforce_password_change(_request("/api" + path), user)  # no raise
            password_change.enforce_password_change(_request(path), user)
        with pytest.raises(HTTPException) as refused:
            password_change.enforce_password_change(_request("/api/customer_portal/overview"), user)
        assert refused.value.status_code == 403
        assert refused.value.headers == {password_change.PASSWORD_CHANGE_HEADER: "true"}
        assert "Choose a new password" in refused.value.detail

    def test_nobody_else_is_held(self):
        overview = _request("/api/customer_portal/overview")
        password_change.enforce_password_change(overview, _user(held=False))
        # The analyst frontend has no forced-change flow yet: the flag is carried, not enforced.
        password_change.enforce_password_change(overview, _user(role=RoleEnum.analyst))
        password_change.enforce_password_change(overview, _user(role=RoleEnum.admin))

    def test_the_route_template_decides_without_the_api_prefix(self):
        assert password_change.route_path(_request("/api/auth/refresh")) == "/auth/refresh"
        assert password_change.route_path(_request("/auth/refresh")) == "/auth/refresh"
        bare = SimpleNamespace(scope={}, url=SimpleNamespace(path="/api/auth/refresh"))
        assert password_change.route_path(bare) == "/auth/refresh"
        # A route that merely starts with the same letters keeps its path.
        assert password_change.route_path(_request("/apiary/x")) == "/apiary/x"

    def test_every_allowed_path_is_a_real_route(self):
        paths = {route.path for route in _routes()}
        allowed = {"/api" + path for path in password_change.ALLOWED_PATHS}
        assert allowed <= paths, allowed - paths


class TestWhereItRuns:
    """Both ways a route authenticates check the hold, so no authenticated route skips it."""

    def _held_session(self):
        return patch.object(AuthHandler, "_resolve_user", AsyncMock(return_value=_user()))

    def _token(self):
        return asyncio.run(_encode("portal1"))

    def test_require_any_scope_refuses_a_held_customer(self):
        guard = AuthHandler().require_any_scope("customer_user")
        with self._held_session(), patch("app.auth.utils.get_role", AsyncMock(return_value="customer_user")):
            token = self._token()
            with pytest.raises(HTTPException) as refused:
                asyncio.run(guard(_request("/api/customer_portal/overview"), token))
            assert refused.value.status_code == 403
            assert asyncio.run(guard(_request("/api/customer_portal/me"), token)) == "portal1"

    def test_get_current_user_refuses_a_held_customer(self):
        with self._held_session(), patch("app.auth.utils.get_role", AsyncMock(return_value="customer_user")):
            token = self._token()
            with pytest.raises(HTTPException) as refused:
                asyncio.run(AuthHandler().get_current_user(_request("/api/incidents/alerts"), SecurityScopes([]), token))
            assert refused.value.headers[password_change.PASSWORD_CHANGE_HEADER] == "true"

    def test_no_route_reads_a_token_without_a_check_that_holds(self):
        """A route that took the bearer token but resolved the user some other way would skip the hold."""

        def calls(dependant):
            yield dependant.call
            for dependency in dependant.dependencies:
                yield from calls(dependency)

        offenders = []
        for route in _routes():
            seen = list(calls(route.dependant))
            reads_token = any(isinstance(call, OAuth2PasswordBearer) for call in seen)
            checked = any(getattr(call, "__name__", "") in ("_require_any_scope", "get_current_user") for call in seen)
            if reads_token and not checked:
                offenders.append((route.path, sorted(route.methods)))
        assert offenders == []


async def _encode(username):
    return await AuthHandler().encode_token(username)


class TestWhoSetsIt:
    def test_a_temporary_password_must_be_replaced(self):
        user = SimpleNamespace(password="old", must_change_password=False)
        session = SimpleNamespace(add=lambda _: None, commit=AsyncMock())
        asyncio.run(security_admin.apply_temporary_password(session, user, security_admin.generate_temporary_password()))
        assert user.must_change_password is True

    def test_an_admin_reset_holds_the_user_but_not_the_admin_resetting_their_own(self):
        admin = _user(role=RoleEnum.admin, held=False, user_id=1, username="admin")
        other = _user(held=False)
        assert password_change.require_change(other, admin) is True and other.must_change_password is True
        assert password_change.require_change(admin, admin) is False and admin.must_change_password is False


class TestTheChange:
    """``POST /auth/reset-password/me``, called directly."""

    def _call(self, user, current, new=NEW_PASSWORD):
        from app.auth.routes import auth as routes

        body = PasswordReset(username=user.username, new_password=new, current_password=current)
        session = SimpleNamespace(add=lambda _: None, commit=AsyncMock())
        handler = AuthHandler()
        user.password = handler.get_password_hash(TEMP_PASSWORD)
        with (
            patch.object(routes, "find_user", AsyncMock(return_value=user)),
            patch.object(routes.auth_handler, "verify_reset_token_me", AsyncMock(return_value=user.username)),
            patch.object(routes, "record_audit_event", AsyncMock()) as update_event,
            patch.object(password_change, "record_audit_event", AsyncMock()) as change_event,
        ):
            result = asyncio.run(routes.reset_password_me(body, SimpleNamespace(), "token", session))
        return result, update_event, change_event

    def test_it_clears_the_hold_and_records_it(self):
        user = _user()
        result, _, change_event = self._call(user, TEMP_PASSWORD)
        assert result["success"] is True and user.must_change_password is False
        assert change_event.await_args.kwargs["action"] == AuditAction.USER_PASSWORD_CHANGE

    def test_a_held_user_must_give_the_password_they_received(self):
        with pytest.raises(HTTPException) as refused:
            self._call(_user(), None)
        assert refused.value.status_code == 400 and "received" in refused.value.detail

    def test_the_new_password_must_differ(self):
        with pytest.raises(HTTPException) as refused:
            self._call(_user(), TEMP_PASSWORD, new=TEMP_PASSWORD)
        assert refused.value.status_code == 400 and "different" in refused.value.detail

    def test_a_wrong_current_password_is_refused_and_the_hold_stays(self):
        user = _user()
        with pytest.raises(HTTPException):
            self._call(user, "Not-The-One-2026!")
        assert user.must_change_password is True

    def test_an_analyst_changes_without_the_current_password_as_before(self):
        # The analyst frontend's own change sends none; analysts carry the flag, unenforced.
        user = _user(role=RoleEnum.analyst)
        result, _, change_event = self._call(user, None)
        assert result["success"] is True and user.must_change_password is False
        assert change_event.await_args.kwargs["action"] == AuditAction.USER_PASSWORD_CHANGE

    def test_an_ordinary_change_records_no_replacement(self):
        user = _user(held=False)
        _, _, change_event = self._call(user, TEMP_PASSWORD)
        change_event.assert_not_awaited()


class TestTheResponse:
    def test_the_apps_error_handler_keeps_the_header(self):
        """It rebuilt the response and dropped the exception's headers: the portal never saw the hold."""
        from app.middleware import exception_handlers as handlers

        refused = HTTPException(403, password_change.PASSWORD_CHANGE_REQUIRED, headers={password_change.PASSWORD_CHANGE_HEADER: "true"})
        logger = SimpleNamespace(log_error=AsyncMock())

        class Session:
            async def __aenter__(self):
                return SimpleNamespace(commit=AsyncMock())

            async def __aexit__(self, *exc):
                return False

        with (
            patch.object(handlers, "AsyncSession", lambda *_: Session()),
            patch.object(handlers, "Logger", lambda *_: logger),
            patch.object(handlers, "get_user_id_from_request", AsyncMock(return_value=None)),
        ):
            response = asyncio.run(handlers.custom_http_exception_handler(_request("/api/customer_portal/overview"), refused))
        assert response.status_code == 403
        assert response.headers[password_change.PASSWORD_CHANGE_HEADER] == "true"

    def test_a_portal_on_another_origin_can_read_it(self):
        import copilot

        cors = next(m for m in copilot.app.user_middleware if m.cls.__name__ == "CORSMiddleware")
        assert password_change.PASSWORD_CHANGE_HEADER in cors.kwargs["expose_headers"]
