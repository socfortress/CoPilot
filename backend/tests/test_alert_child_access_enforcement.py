"""Per-object access on the alert child-object routes and bulk case linking (#1102).

Follow-up to #1099/#1101, which covered bulk delete and single assign. The routes
below mutate an alert (or attach one to a case) by id and had no access check at
all -- most of them took no `current_user` to check against.

Two are worth calling out beyond the general tenancy point:

* `DELETE /alert/tag` is not cosmetic. `user_tag_access` / `role_tag_access` gate
  which alerts a user can see when tag ACLs are on, so removing the tag that
  scopes an alert changes who can see it.
* `POST /alert` takes `customer_code` straight from the request body, so without
  a check a scoped analyst can file an alert against any tenant.

`POST /case/alert-links` fails the request on a denied alert rather than skipping
it, unlike bulk delete: there is no partial-success shape in its response, and
the caller builds the list from alerts it can already see.

Unit tests against the route handlers with a mocked session; no real DB.

Run with: cd backend && python -m pytest tests/test_alert_child_access_enforcement.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.routes.db_operations as routes  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.schema.db_operations import AlertCreate  # noqa: E402
from app.incidents.schema.db_operations import AlertIoCCreate  # noqa: E402
from app.incidents.schema.db_operations import AlertIoCDelete  # noqa: E402
from app.incidents.schema.db_operations import AlertTagCreate  # noqa: E402
from app.incidents.schema.db_operations import AlertTagDelete  # noqa: E402
from app.incidents.schema.db_operations import AssetCreate  # noqa: E402
from app.incidents.schema.db_operations import CaseAlertLinksCreate  # noqa: E402

ANALYST = SimpleNamespace(id=7, username="analyst", role_id=2)

OWN_ID = 1
FOREIGN_ID = 2
OWN_CASE = 10
FOREIGN_CASE = 20
OWN_CUSTOMER = "TENANT_A"
FOREIGN_CUSTOMER = "TENANT_B"


def _patch_access(monkeypatch):
    """The three helpers, each denying the foreign object."""

    async def ensure_alert(alert_id, current_user, db):
        if alert_id == FOREIGN_ID:
            raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id}")
        return SimpleNamespace(id=alert_id, customer_code=OWN_CUSTOMER)

    async def ensure_case(case_id, current_user, db):
        if case_id == FOREIGN_CASE:
            raise HTTPException(status_code=403, detail=f"Access denied to case {case_id}")

    async def ensure_customer(customer_code, current_user, db):
        if customer_code == FOREIGN_CUSTOMER:
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")

    monkeypatch.setattr(routes, "_ensure_alert_access", ensure_alert)
    monkeypatch.setattr(routes, "_ensure_case_access", ensure_case)
    monkeypatch.setattr(routes, "_ensure_customer_access", ensure_customer)


def _alert_create(customer_code):
    return AlertCreate(
        alert_name="Alert",
        alert_description="Description",
        status="OPEN",
        alert_creation_time=datetime(2026, 8, 26, 12, 0, 0),
        customer_code=customer_code,
        source="wazuh",
        assigned_to="analyst",
    )


def _denied(coro_factory):
    """Run a handler expected to 403, returning the exception."""
    with pytest.raises(HTTPException) as exc:
        asyncio.run(coro_factory())
    return exc.value


# ------------------------------------------------------- alert creation and children


def test_create_alert_refuses_a_foreign_customer(monkeypatch):
    """`customer_code` is caller-supplied, so it has to be checked like /case/create."""
    _patch_access(monkeypatch)
    created = AsyncMock()
    monkeypatch.setattr(routes, "create_alert", created)

    error = _denied(
        lambda: routes.create_alert_endpoint(
            _alert_create(FOREIGN_CUSTOMER),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    created.assert_not_awaited()


def test_create_alert_still_works_for_an_entitled_customer(monkeypatch):
    _patch_access(monkeypatch)
    created = AsyncMock(return_value=SimpleNamespace(id=1))
    monkeypatch.setattr(routes, "create_alert", created)

    asyncio.run(
        routes.create_alert_endpoint(
            _alert_create(OWN_CUSTOMER),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    created.assert_awaited_once()


def test_create_asset_refuses_a_foreign_alert(monkeypatch):
    """This schema calls the alert id `alert_linked`, which is why it was missed."""
    _patch_access(monkeypatch)
    created = AsyncMock()
    monkeypatch.setattr(routes, "create_asset", created)

    error = _denied(
        lambda: routes.create_asset_endpoint(
            AssetCreate(
                alert_linked=FOREIGN_ID,
                asset_name="host",
                alert_context_id=1,
                customer_code=FOREIGN_CUSTOMER,
                index_name="wazuh-alerts",
                index_id="abc123",
            ),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    created.assert_not_awaited()


def test_create_alert_ioc_refuses_a_foreign_alert(monkeypatch):
    _patch_access(monkeypatch)
    created = AsyncMock()
    monkeypatch.setattr(routes, "create_alert_ioc", created)

    error = _denied(
        lambda: routes.create_alert_ioc_endpoint(
            AlertIoCCreate(alert_id=FOREIGN_ID, ioc_value="1.2.3.4", ioc_type="IP"),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    created.assert_not_awaited()


def test_delete_alert_ioc_refuses_a_foreign_alert(monkeypatch):
    _patch_access(monkeypatch)
    deleted = AsyncMock()
    monkeypatch.setattr(routes, "delete_alert_ioc", deleted)

    error = _denied(
        lambda: routes.delete_alert_ioc_endpoint(
            AlertIoCDelete(alert_id=FOREIGN_ID, ioc_id=5),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    deleted.assert_not_awaited()


def test_create_alert_tag_refuses_a_foreign_alert(monkeypatch):
    _patch_access(monkeypatch)
    created = AsyncMock()
    monkeypatch.setattr(routes, "create_alert_tag", created)

    error = _denied(
        lambda: routes.create_alert_tag_endpoint(
            AlertTagCreate(alert_id=FOREIGN_ID, tag="malware"),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    created.assert_not_awaited()


def test_delete_alert_tag_refuses_a_foreign_alert(monkeypatch):
    """The one with teeth: tags gate visibility when tag ACLs are enabled, so an
    unscoped tag delete is an access-control mutation."""
    _patch_access(monkeypatch)
    deleted = AsyncMock()
    monkeypatch.setattr(routes, "delete_alert_tag", deleted)

    error = _denied(
        lambda: routes.delete_alert_tag_endpoint(
            AlertTagDelete(alert_id=FOREIGN_ID, tag_id=3),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    deleted.assert_not_awaited()


def test_delete_alert_tag_still_works_on_an_accessible_alert(monkeypatch):
    """The check must not break ordinary tag management."""
    _patch_access(monkeypatch)
    monkeypatch.setattr(routes, "delete_alert_tag", AsyncMock(return_value=AlertTag(id=3, tag="malware")))

    response = asyncio.run(
        routes.delete_alert_tag_endpoint(
            AlertTagDelete(alert_id=OWN_ID, tag_id=3),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert response.success is True
    assert response.alert_tag.tag == "malware"


# ------------------------------------------------------------------ bulk case links


def _patch_links(monkeypatch, links=None):
    created = AsyncMock(return_value=links or [])
    monkeypatch.setattr(routes, "create_case_alert_links_bulk", created)

    import app.incidents.services.case_events as case_events

    monkeypatch.setattr(case_events, "emit_case_event", AsyncMock())
    return created


def test_bulk_case_links_refuses_a_foreign_alert(monkeypatch):
    """One foreign alert in the list fails the request; nothing is linked.

    Deliberately unlike bulk delete, which skips: this response has no
    partial-success shape, and the caller builds the list from alerts it can see.
    """
    _patch_access(monkeypatch)
    created = _patch_links(monkeypatch)

    error = _denied(
        lambda: routes.create_case_alert_links_endpoint(
            CaseAlertLinksCreate(case_id=OWN_CASE, alert_ids=[OWN_ID, FOREIGN_ID]),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    created.assert_not_awaited()


def test_bulk_case_links_refuses_a_foreign_case(monkeypatch):
    """Both ends are checked, as the single-alert link route does."""
    _patch_access(monkeypatch)
    created = _patch_links(monkeypatch)

    error = _denied(
        lambda: routes.create_case_alert_links_endpoint(
            CaseAlertLinksCreate(case_id=FOREIGN_CASE, alert_ids=[OWN_ID]),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert error.status_code == 403
    created.assert_not_awaited()


def test_bulk_case_links_still_works_when_everything_is_accessible(monkeypatch):
    _patch_access(monkeypatch)
    created = _patch_links(monkeypatch, links=[CaseAlertLink(case_id=OWN_CASE, alert_id=OWN_ID)])

    response = asyncio.run(
        routes.create_case_alert_links_endpoint(
            CaseAlertLinksCreate(case_id=OWN_CASE, alert_ids=[OWN_ID]),
            current_user=ANALYST,
            db=AsyncMock(),
        ),
    )

    assert response.success is True
    created.assert_awaited_once()
