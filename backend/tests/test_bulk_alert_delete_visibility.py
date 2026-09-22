"""``DELETE /incidents/db_operations/alerts/by-title/{title_filter}`` must honour alert visibility.

Before this test the route filtered candidates by customer only, so a tag-restricted
analyst could bulk-delete alerts the list (and the single-alert delete) would have
refused to show them. It now goes through ``alert_visibility_filters_for_user`` —
the same builder the counts and listings use.

Pure unit tests: the visibility builder and the session are patched, no DB.

Run with: cd backend && python -m pytest tests/test_bulk_alert_delete_visibility.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.incidents.models import Alert  # noqa: E402
from app.incidents.routes import db_operations as routes  # noqa: E402

USER = SimpleNamespace(id=7, username="scoped-analyst", role_id=2)


def _run(visibility, alerts):
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = alerts
    db.execute = AsyncMock(return_value=result)
    with (
        patch.object(routes, "alert_visibility_filters_for_user", AsyncMock(return_value=visibility)),
        patch.object(routes, "is_alert_linked_to_case", AsyncMock()),
        patch.object(routes, "delete_alert", AsyncMock()) as delete_alert,
    ):
        response = asyncio.run(routes.delete_alerts_by_title_endpoint("File", current_user=USER, db=db))
    return response, db, delete_alert


def test_user_who_can_see_nothing_deletes_nothing_and_never_queries():
    response, db, delete_alert = _run(visibility=None, alerts=[])
    assert response.deleted_alert_ids == []
    db.execute.assert_not_awaited()
    delete_alert.assert_not_awaited()


def test_visibility_clauses_are_applied_next_to_the_title_filter():
    tag_clause = Alert.customer_code.in_(["ACME"])
    response, db, delete_alert = _run(visibility=[tag_clause], alerts=[SimpleNamespace(id=11)])

    stmt = db.execute.await_args.args[0]
    criteria = list(stmt.whereclause.clauses)
    assert len(criteria) == 2, "expected title ILIKE plus the visibility clause"
    assert any(c is tag_clause for c in criteria)

    assert response.deleted_alert_ids == [11]
    delete_alert.assert_awaited_once_with(11, db)
