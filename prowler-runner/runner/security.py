"""The bearer token every /v1 route requires."""

from __future__ import annotations

import hmac

from fastapi import Request

from runner.errors import RunnerError


def require_token(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.token_configured:
        raise RunnerError(503, "not_configured")
    scheme, _, presented = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(presented.strip().encode(), settings.token.encode()):
        raise RunnerError(401, "unauthorized")
