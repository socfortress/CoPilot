"""Abandoned requests must stop being served (#1072, level 1).

Starlette runs a handler to completion even after the client has gone: the
response is written into a closed socket. On this deployment that means a 34s
Elasticsearch query still running half a minute after the user navigated away.

The frontend already aborts obsolete requests, which closes the socket. This is
the server half. The three rules that keep it from doing harm are asserted here,
because each one fails silently and expensively if broken:

* mutations are never cancelled (cancelling one destroys the caller's knowledge
  of whether it happened, without undoing it);
* streaming endpoints are excluded (holding the connection open is the feature);
* a handler that reads the request body still receives every message, even though
  the middleware now owns the receive channel.

Run with: cd backend && python -m pytest tests/test_client_disconnect_cancellation.py
"""

import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.middleware.client_disconnect import SCOPE_FLAG  # noqa: E402
from app.middleware.client_disconnect import ClientDisconnectMiddleware  # noqa: E402


def _scope(method="GET", path="/api/vulnerabilities/search"):
    return {"type": "http", "method": method, "path": path, "headers": []}


class _Client:
    """Drives one request, and can hang up part-way through."""

    def __init__(self):
        self.sent = []
        self._messages = asyncio.Queue()
        self._messages.put_nowait({"type": "http.request", "body": b"", "more_body": False})

    async def receive(self):
        return await self._messages.get()

    async def send(self, message):
        self.sent.append(message)

    def hang_up(self):
        self._messages.put_nowait({"type": "http.disconnect"})


def _run(app, client, scope, after=None):
    """Drive the middleware, optionally doing something once the app has started."""

    async def scenario():
        middleware = ClientDisconnectMiddleware(app)
        task = asyncio.create_task(middleware(scope, client.receive, client.send))
        await asyncio.sleep(0.05)
        if after is not None:
            after()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(scenario())


def test_an_abandoned_get_is_cancelled():
    """The failure mode: a long query still running for a client that left."""
    finished = False

    async def slow_app(scope, receive, send):
        nonlocal finished
        await asyncio.sleep(5)  # stands in for a 30s Elasticsearch query
        finished = True
        await send({"type": "http.response.start", "status": 200, "headers": []})

    client = _Client()
    scope = _scope()
    _run(slow_app, client, scope, after=client.hang_up)

    assert not finished, "the handler kept working after the client disconnected"
    assert client.sent == [], "nothing should be written to a closed socket"
    assert scope.get(SCOPE_FLAG) is True, "the request should be marked abandoned for the metrics"


def test_a_completed_request_is_untouched():
    async def fast_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    client = _Client()
    scope = _scope()
    _run(fast_app, client, scope)

    assert [m["type"] for m in client.sent] == ["http.response.start", "http.response.body"]
    assert SCOPE_FLAG not in scope


def test_a_mutation_is_never_cancelled():
    """Aborting a POST does not undo it — it only hides whether it happened."""
    finished = False

    async def mutating_app(scope, receive, send):
        nonlocal finished
        await asyncio.sleep(0.3)
        finished = True
        await send({"type": "http.response.start", "status": 201, "headers": []})

    client = _Client()
    scope = _scope(method="POST", path="/api/incidents/cases")
    _run(mutating_app, client, scope, after=client.hang_up)

    assert finished, "a POST must run to completion even if the client leaves"
    assert scope.get(SCOPE_FLAG) is None


def test_streaming_endpoints_are_excluded():
    """Holding the connection open is what these endpoints are for."""
    finished = False

    async def streaming_app(scope, receive, send):
        nonlocal finished
        await asyncio.sleep(0.3)
        finished = True

    client = _Client()
    scope = _scope(path="/api/agents/sca/overview/stream")
    _run(streaming_app, client, scope, after=client.hang_up)

    assert finished, "an excluded path must not be cancelled by this middleware"


def test_the_handler_still_receives_every_message():
    """The middleware owns the receive channel but must not swallow anything."""
    seen = []

    async def body_reading_app(scope, receive, send):
        seen.append(await receive())
        await send({"type": "http.response.start", "status": 200, "headers": []})

    client = _Client()
    _run(body_reading_app, client, _scope())

    assert [m["type"] for m in seen] == ["http.request"]


def test_a_handler_error_still_propagates():
    """Cancellation must not swallow real failures — the 500 path still works."""

    class Boom(Exception):
        pass

    async def failing_app(scope, receive, send):
        raise Boom("handler exploded")

    async def scenario():
        middleware = ClientDisconnectMiddleware(failing_app)
        client = _Client()
        await middleware(_scope(), client.receive, client.send)

    try:
        asyncio.run(scenario())
        raised = None
    except Boom as exc:
        raised = exc

    assert raised is not None, "the handler's exception must reach the error handlers"


def test_a_served_request_is_never_cancelled_during_teardown():
    """The response is out: hanging up now saves nothing and risks a leak.

    FastAPI keeps unwinding after the last byte — `Depends(get_db)` closes its
    session in the `async with` teardown, which is an await point. Cancelling
    there can leave a connection unreturned to the pool. A real session showed 19
    requests cancelled *after* answering with a 200; none of them saved any work.
    """
    torn_down = False

    async def app_with_teardown(scope, receive, send):
        nonlocal torn_down
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
        # Stands in for the dependency teardown that returns a DB connection.
        await asyncio.sleep(0.2)
        torn_down = True

    client = _Client()
    scope = _scope()
    _run(app_with_teardown, client, scope, after=client.hang_up)

    assert torn_down, "teardown after a sent response must be allowed to finish"
    assert SCOPE_FLAG not in scope, "an answered request is not an abandoned one"


def test_a_partially_sent_response_is_still_cancelled():
    """Only a *complete* response earns immunity."""
    finished = False

    async def slow_body_app(scope, receive, send):
        nonlocal finished
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"chunk", "more_body": True})
        await asyncio.sleep(5)
        finished = True

    client = _Client()
    scope = _scope()
    _run(slow_body_app, client, scope, after=client.hang_up)

    assert not finished, "a response still being written must be cancellable"
    assert scope.get(SCOPE_FLAG) is True


def test_disconnect_after_completion_changes_nothing():
    """A client that hangs up as the response lands must not flag the request."""

    async def fast_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    client = _Client()
    scope = _scope()

    async def scenario():
        middleware = ClientDisconnectMiddleware(fast_app)
        await middleware(scope, client.receive, client.send)
        client.hang_up()

    asyncio.run(scenario())

    assert SCOPE_FLAG not in scope
    assert len(client.sent) == 2
