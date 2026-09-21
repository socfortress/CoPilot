"""Huntress collection must not leak credentials, and must not report success when it failed.

Two defects reported together by an operator running `copilot-backend:latest`:

* Every collection run logged the whole `CollectHuntress` payload at INFO — Wazuh Indexer
  username/password plus the Huntress API key and secret — into the backend's docker logs. The
  module container did the same on its side and additionally logged the base64 Basic-auth string,
  which is an encoding, not encryption.
* The `copilot-huntress-module` container is optional and is deliberately not part of the default
  docker-compose stack. When it is absent the POST fails with `[Errno -2] Name or service not
  known`, but the response was discarded, the route turned the exception into a *returned*
  `success=False`, and the job stamped `last_success` unconditionally. The scheduler therefore
  reported a healthy Huntress job that had never shipped a single event.

These tests pin: secrets masked in the log line but intact on the wire, a non-2xx module response
raising, a missing container producing an actionable error, and the job raising — rather than
returning — when any customer failed, since `last_success` is stamped centrally on
EVENT_JOB_EXECUTED and so is skipped only when the callable raises.

No DB, no network. Run with: cd backend && python -m pytest tests/test_huntress_collection_failure.py
"""

import asyncio
import contextlib
import json
import os
import types

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations.modules.schema.huntress import CollectHuntress  # noqa: E402
from app.integrations.modules.schema.huntress import (  # noqa: E402
    InvokeHuntressResponse,
)
from app.integrations.modules.services import huntress as huntress_service  # noqa: E402
from app.schedulers.services import invoke_huntress as invoke_huntress_module  # noqa: E402

SECRETS = ("wazuh-pw-9f3a", "huntress-key-7b21", "huntress-secret-4c88")


def _payload():
    return CollectHuntress(
        integration="huntress",
        customer_code="cyfox",
        graylog_host="graylog",
        graylog_port="12201",
        wazuh_indexer_host="https://wazuh-indexer:9200",
        wazuh_indexer_username="admin",
        wazuh_indexer_password=SECRETS[0],
        api_key=SECRETS[1],
        api_secret=SECRETS[2],
    )


# --- credentials -----------------------------------------------------------------------------


def test_rendering_the_payload_does_not_expose_credentials():
    """This is the exact interpolation the service performs when it logs the request."""
    rendered = f"{_payload()}"

    for secret in SECRETS:
        assert secret not in rendered
    assert rendered.count("**********") == 3
    # Non-secret context stays readable, otherwise the log line is useless for debugging.
    assert "cyfox" in rendered


def test_to_wire_restores_the_real_values():
    """Masking must not reach the module: it needs the actual credentials to authenticate."""
    wire = _payload().to_wire()

    assert wire["wazuh_indexer_password"] == SECRETS[0]
    assert wire["api_key"] == SECRETS[1]
    assert wire["api_secret"] == SECRETS[2]
    # httpx serializes the body with json.dumps; SecretStr objects would raise here.
    assert SECRETS[1] in json.dumps(wire)


def test_model_dump_alone_is_not_usable_as_a_request_body():
    """The trap this guards: `json=data.model_dump()` silently ships masked credentials."""
    dumped = _payload().model_dump(mode="json")

    assert dumped["api_key"] == "**********"


# --- module transport ------------------------------------------------------------------------


def _fake_httpx(handler):
    """Replace the service's `httpx` with a stub whose client runs `handler`.

    `ConnectError` is the real class so the service's `except` clause still matches it.
    """

    class _FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def post(self, url, **kwargs):
            return handler(url, **kwargs)

    return types.SimpleNamespace(AsyncClient=_FakeAsyncClient, ConnectError=httpx.ConnectError)


def test_module_error_status_raises(monkeypatch):
    def handler(url, **kwargs):
        return httpx.Response(500, request=httpx.Request("POST", url), text="boom")

    monkeypatch.setattr(huntress_service, "httpx", _fake_httpx(handler))

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(huntress_service.post_to_copilot_huntress_module(_payload()))


def test_unreachable_module_says_the_container_is_optional(monkeypatch):
    """`Name or service not known` on its own sends operators hunting for a network fault."""

    def handler(url, **kwargs):
        raise httpx.ConnectError("[Errno -2] Name or service not known")

    monkeypatch.setattr(huntress_service, "httpx", _fake_httpx(handler))

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(huntress_service.post_to_copilot_huntress_module(_payload()))

    message = str(excinfo.value)
    assert "ghcr.io/socfortress/copilot-huntress-module" in message
    assert "Name or service not known" in message


def test_successful_post_sends_the_unmasked_body(monkeypatch):
    sent = {}

    def handler(url, **kwargs):
        sent.update(kwargs["json"])
        return httpx.Response(200, request=httpx.Request("POST", url), json={"success": True})

    monkeypatch.setattr(huntress_service, "httpx", _fake_httpx(handler))
    asyncio.run(huntress_service.post_to_copilot_huntress_module(_payload()))

    assert sent["api_key"] == SECRETS[1]
    assert sent["api_secret"] == SECRETS[2]


# --- scheduled job ---------------------------------------------------------------------------


def _install_fake_db(monkeypatch, customer_codes):
    class _Result:
        def scalars(self):
            return [types.SimpleNamespace(customer_code=code) for code in customer_codes]

    class _Session:
        async def execute(self, _stmt):
            return _Result()

    @contextlib.asynccontextmanager
    async def _get_db_session():
        yield _Session()

    monkeypatch.setattr(invoke_huntress_module, "get_db_session", _get_db_session)

    async def _metadata(_job_id):
        return types.SimpleNamespace(time_interval=5)

    monkeypatch.setattr(invoke_huntress_module, "get_scheduled_job_metadata", _metadata)


def test_job_returns_when_every_customer_collects(monkeypatch):
    _install_fake_db(monkeypatch, ["cyfox", "acme"])

    async def _route(_request, _session):
        return InvokeHuntressResponse(success=True, message="ok")

    monkeypatch.setattr(invoke_huntress_module, "collect_huntress_route", _route)

    result = asyncio.run(invoke_huntress_module.invoke_huntress_integration_collect())

    assert result.success is True
    assert "2 customer(s)" in result.message


def test_job_raises_when_the_route_reports_failure(monkeypatch):
    """The regression: the route *returns* success=False, so only re-raising marks the run bad."""
    _install_fake_db(monkeypatch, ["cyfox"])

    async def _route(_request, _session):
        return InvokeHuntressResponse(success=False, message="Name or service not known")

    monkeypatch.setattr(invoke_huntress_module, "collect_huntress_route", _route)

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(invoke_huntress_module.invoke_huntress_integration_collect())

    assert "cyfox" in str(excinfo.value)


def test_one_customers_failure_does_not_skip_the_others(monkeypatch):
    _install_fake_db(monkeypatch, ["broken", "healthy"])
    attempted = []

    async def _route(request, _session):
        attempted.append(request.customer_code)
        if request.customer_code == "broken":
            raise RuntimeError("module unreachable")
        return InvokeHuntressResponse(success=True, message="ok")

    monkeypatch.setattr(invoke_huntress_module, "collect_huntress_route", _route)

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(invoke_huntress_module.invoke_huntress_integration_collect())

    assert attempted == ["broken", "healthy"]
    assert "1 of 2" in str(excinfo.value)
