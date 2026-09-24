"""Comment authorship on alerts and cases.

Three holes closed in the comment routes of app/incidents/routes/db_operations.py:

1. ``user_name`` came from the request body, so anyone could post or edit as someone
   else (a customer signing as a SOC analyst). The routes now stamp the caller.
2. A customer_user could edit or delete any comment on an alert/case they can see,
   analysts' included. They may now change only their own; admin/analyst still moderate.
3. The edit routes checked access on the body's alert_id/case_id but edited the comment
   named by comment_id, so a caller could pass their own alert and a comment id from
   another tenant. The comment itself now decides what is checked.

Unit tests against the route functions with a mocked session; no real DB.

Run with: cd backend && python -m pytest tests/test_comment_authorship.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.incidents.routes.db_operations as dbo  # noqa: E402
from app.incidents.schema.db_operations import CaseCommentCreate  # noqa: E402
from app.incidents.schema.db_operations import CaseCommentEdit  # noqa: E402
from app.incidents.schema.db_operations import CommentCreate  # noqa: E402
from app.incidents.schema.db_operations import CommentEdit  # noqa: E402

CUSTOMER = SimpleNamespace(id=10, username="customer1", role_id=4)
ANALYST = SimpleNamespace(id=2, username="analyst1", role_id=2)


def _session_returning(row):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    session.execute = AsyncMock(return_value=result)
    return session


def _access(allowed=True):
    return patch.object(dbo.customer_access_handler, "check_customer_access", AsyncMock(return_value=allowed))


def _alert_edit(**overrides):
    data = {"alert_id": 1, "comment_id": 5, "comment": "edited", "user_name": "customer1", "created_at": datetime.utcnow()}
    return CommentEdit(**{**data, **overrides})


def _case_edit(**overrides):
    data = {"case_id": 1, "comment_id": 5, "comment": "edited", "user_name": "customer1", "created_at": datetime.utcnow()}
    return CaseCommentEdit(**{**data, **overrides})


# ── author is stamped from the caller ─────────────────────────────────────


def test_alert_comment_create_ignores_the_body_author():
    create = AsyncMock(side_effect=lambda comment, db: comment)
    body = CommentCreate(alert_id=1, comment="hi", user_name="analyst1")
    with patch.object(dbo, "get_alert_by_id", AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access(), patch.object(
        dbo,
        "create_comment",
        create,
    ), patch.object(dbo, "CommentResponse", lambda **kw: kw):
        asyncio.run(dbo.create_comment_endpoint(body, CUSTOMER, AsyncMock()))
    assert create.await_args.args[0].user_name == "customer1"


def test_case_comment_create_ignores_the_body_author():
    create = AsyncMock(return_value=SimpleNamespace(id=1, comment="hi"))
    body = CaseCommentCreate(case_id=1, comment="hi", user_name="analyst1")
    with patch.object(dbo, "get_case_by_id", AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access(), patch.object(
        dbo,
        "create_case_comment",
        create,
    ), patch("app.incidents.services.case_events.emit_case_event", AsyncMock()), patch.object(
        dbo,
        "CaseCommentResponse",
        lambda **kw: kw,
    ):
        asyncio.run(dbo.create_case_comment_endpoint(body, CUSTOMER, AsyncMock()))
    assert create.await_args.args[0].user_name == "customer1"


def test_edit_stamps_the_editor_not_the_body_author():
    edit = AsyncMock(side_effect=lambda comment, db: comment)
    existing = SimpleNamespace(id=5, alert_id=1, user_name="customer1")
    with patch.object(dbo, "get_alert_by_id", AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access(), patch.object(
        dbo,
        "edit_comment",
        edit,
    ), patch.object(dbo, "CommentResponse", lambda **kw: kw):
        asyncio.run(dbo.edit_comment_endpoint(_alert_edit(user_name="analyst1"), CUSTOMER, _session_returning(existing)))
    assert edit.await_args.args[0].user_name == "customer1"


# ── customers change only their own comments ──────────────────────────────


@pytest.mark.parametrize("endpoint, body, parent", [("alert", _alert_edit, "get_alert_by_id"), ("case", _case_edit, "get_case_by_id")])
def test_customer_cannot_edit_someone_elses_comment(endpoint, body, parent):
    existing = SimpleNamespace(id=5, alert_id=1, case_id=1, user_name="analyst1")
    route = dbo.edit_comment_endpoint if endpoint == "alert" else dbo.edit_case_comment_endpoint
    with patch.object(dbo, parent, AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access():
        with pytest.raises(HTTPException) as exc:
            asyncio.run(route(body(), CUSTOMER, _session_returning(existing)))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("endpoint, parent", [("alert", "get_alert_by_id"), ("case", "get_case_by_id")])
def test_customer_cannot_delete_someone_elses_comment(endpoint, parent):
    existing = SimpleNamespace(id=5, alert_id=1, case_id=1, user_name="analyst1")
    route = dbo.delete_comment_endpoint if endpoint == "alert" else dbo.delete_case_comment_endpoint
    remover = "delete_comment" if endpoint == "alert" else "delete_case_comment"
    delete = AsyncMock()
    with patch.object(dbo, parent, AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access(), patch.object(
        dbo,
        remover,
        delete,
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(route(5, CUSTOMER, _session_returning(existing)))
    assert exc.value.status_code == 403
    delete.assert_not_awaited()


@pytest.mark.parametrize("endpoint, parent", [("alert", "get_alert_by_id"), ("case", "get_case_by_id")])
def test_customer_can_delete_their_own_comment(endpoint, parent):
    existing = SimpleNamespace(id=5, alert_id=1, case_id=1, user_name="customer1")
    route = dbo.delete_comment_endpoint if endpoint == "alert" else dbo.delete_case_comment_endpoint
    remover = "delete_comment" if endpoint == "alert" else "delete_case_comment"
    delete = AsyncMock()
    with patch.object(dbo, parent, AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access(), patch.object(
        dbo,
        remover,
        delete,
    ):
        asyncio.run(route(5, CUSTOMER, _session_returning(existing)))
    delete.assert_awaited_once()


@pytest.mark.parametrize("endpoint, parent", [("alert", "get_alert_by_id"), ("case", "get_case_by_id")])
def test_analyst_still_moderates_any_comment(endpoint, parent):
    existing = SimpleNamespace(id=5, alert_id=1, case_id=1, user_name="customer1")
    route = dbo.delete_comment_endpoint if endpoint == "alert" else dbo.delete_case_comment_endpoint
    remover = "delete_comment" if endpoint == "alert" else "delete_case_comment"
    delete = AsyncMock()
    with patch.object(dbo, parent, AsyncMock(return_value=SimpleNamespace(customer_code="A"))), _access(), patch.object(
        dbo,
        remover,
        delete,
    ):
        asyncio.run(route(5, ANALYST, _session_returning(existing)))
    delete.assert_awaited_once()


# ── the comment, not the body, decides which alert/case is checked ────────


@pytest.mark.parametrize("endpoint, body", [("alert", _alert_edit), ("case", _case_edit)])
def test_edit_rejects_a_comment_from_another_parent(endpoint, body):
    # The caller names their own alert/case (1) but a comment that lives on 99.
    existing = SimpleNamespace(id=5, alert_id=99, case_id=99, user_name="customer1")
    route = dbo.edit_comment_endpoint if endpoint == "alert" else dbo.edit_case_comment_endpoint
    with pytest.raises(HTTPException) as exc:
        asyncio.run(route(body(), CUSTOMER, _session_returning(existing)))
    assert exc.value.status_code == 404


@pytest.mark.parametrize("endpoint, body", [("alert", _alert_edit), ("case", _case_edit)])
def test_edit_of_a_missing_comment_is_404(endpoint, body):
    route = dbo.edit_comment_endpoint if endpoint == "alert" else dbo.edit_case_comment_endpoint
    with pytest.raises(HTTPException) as exc:
        asyncio.run(route(body(), CUSTOMER, _session_returning(None)))
    assert exc.value.status_code == 404
