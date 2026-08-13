"""Internal-scope route CRUD.

Internal routes belong to no tenant, so they can't live under
`/customers/{code}/notification_routes` — there's no code to put in the path.
They're where assignment notifications land, which makes them the mechanism that
keeps analyst chatter out of a customer's channel.

Three invariants these tests exist to hold:

1. **Scope is fixed.** A route created here is internal, and stays internal. A
   PATCH that flipped it would strand the route in a scope its dispatch path
   can't reach — it would have no customer_code, so the customer-scoped lookup
   would never find it, and it would silently stop firing.
2. **No customer_code.** The whole point.
3. **No Shuffle.** `shuffle_integration_id` is an FK to a per-customer table.

Unit tests with a mocked session — no DB.

Run with: cd backend && python -m pytest tests/test_notification_internal_routes.py
"""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.notifications.services.notifications as svc  # noqa: E402
from app.notifications.schema.notifications import NotificationRouteCreate  # noqa: E402
from app.notifications.schema.notifications import NotificationRouteUpdate  # noqa: E402


def _payload(**over):
    base = dict(
        name="SOC assignments",
        trigger="alert_assigned",
        channel="resend",
        scope="internal",
        recipient_mode="assignee",
        min_severity="Informational",
        enabled=True,
        config={},
    )
    base.update(over)
    return NotificationRouteCreate(**base)


def _session(existing=None):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


def _existing(route_id=1, channel="resend", scope="internal"):
    return SimpleNamespace(
        id=route_id,
        scope=scope,
        channel=channel,
        customer_code=None,
        recipient_mode="assignee",
        config=json.dumps({"to": []}),
        template_id=None,
        trigger="alert_assigned",
        updated_at=None,
    )


def _added(session):
    assert session.add.call_count == 1
    return session.add.call_args.args[0]


# ── creation ──────────────────────────────────────────────────────────────


def test_created_route_has_no_customer():
    session = _session()
    asyncio.run(svc.create_internal_route(_payload(), "admin", session))
    assert _added(session).customer_code is None


def test_created_route_is_internal_scope():
    session = _session()
    asyncio.run(svc.create_internal_route(_payload(), "admin", session))
    assert _added(session).scope == "internal"


def test_a_customer_scoped_payload_is_rejected_here():
    """Honouring it would create a route with no customer_code that the
    customer-scoped dispatch path could never find."""
    session = _session()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            svc.create_internal_route(_payload(scope="customer", recipient_mode="static", config={"to": ["a@b.c"]}), "admin", session),
        )
    assert exc.value.status_code == 400
    assert session.add.call_count == 0


def test_shuffle_is_rejected_for_internal_routes():
    """A Shuffle integration belongs to a specific customer; an internal route
    belongs to none. Caught at create time rather than surfacing later as a
    confusing "integration is missing" dispatch failure."""
    session = _session()
    payload = _payload(channel="shuffle", recipient_mode="static", destination="#soc", config={"app_id": "x"}, shuffle_integration_id=1)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_internal_route(payload, "admin", session))

    assert exc.value.status_code == 400
    assert "not available for internal routes" in exc.value.detail
    assert session.add.call_count == 0


def test_shuffle_integration_id_is_never_persisted():
    session = _session()
    asyncio.run(svc.create_internal_route(_payload(), "admin", session))
    assert _added(session).shuffle_integration_id is None


def test_assignee_mode_survives_creation():
    """The reason internal routes exist: mail whoever it was assigned to."""
    session = _session()
    asyncio.run(svc.create_internal_route(_payload(), "admin", session))
    assert _added(session).recipient_mode == "assignee"


# ── lookup isolation ──────────────────────────────────────────────────────


def test_lookup_is_scoped_so_a_customer_route_id_is_unreachable():
    """Without the scope predicate, an admin could PATCH a customer's route
    through the internal endpoints."""
    session = _session(existing=None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_internal_route(99, session))
    assert exc.value.status_code == 404

    where = str(session.execute.await_args.args[0])
    assert "scope" in where


def test_list_filters_to_internal_only():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)

    asyncio.run(svc.list_internal_routes(session))
    assert "scope" in str(session.execute.await_args.args[0])


# ── updates ───────────────────────────────────────────────────────────────


def test_scope_cannot_be_changed_by_patch():
    """Flipping scope would leave the route with no customer_code but a
    customer scope — invisible to both dispatch paths."""
    session = _session(existing=_existing())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.update_internal_route(1, NotificationRouteUpdate(scope="customer"), session))
    assert exc.value.status_code == 400


def test_patching_to_shuffle_is_rejected():
    session = _session(existing=_existing())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.update_internal_route(1, NotificationRouteUpdate(channel="shuffle"), session))
    assert exc.value.status_code == 400


def test_recipient_mode_is_validated_against_the_channel():
    """webhook can't resolve a person, so assignee mode on it is a 400 rather
    than a route that silently never delivers."""
    session = _session(existing=_existing(channel="webhook"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            svc.update_internal_route(
                1,
                NotificationRouteUpdate(channel="webhook", recipient_mode="assignee", config={"url": "https://x.invalid"}),
                session,
            ),
        )
    assert exc.value.status_code == 400
    assert "recipient_mode" in exc.value.detail


def test_an_ordinary_field_update_still_works():
    route = _existing()
    session = _session(existing=route)
    asyncio.run(svc.update_internal_route(1, NotificationRouteUpdate(name="Renamed"), session))
    assert route.name == "Renamed"
