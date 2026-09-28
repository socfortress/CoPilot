"""The one definition of which alerts a user may see: ``alert_visibility_filters_for_user``.

Counts, listings, bulk deletes and the Customer Portal's AI report surface all go
through it, so a customer or tag ACL change is made once. These pin its contract:

- ``None`` means "sees nothing" and callers must short-circuit, never run the query;
- ``[]`` means "sees everything" (wildcard customers and tags);
- otherwise a list of WHERE clauses.

Run with: cd backend && python -m pytest tests/test_alert_visibility_filters.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_portal.services.ai_reports as portal_ai  # noqa: E402
import app.incidents.services.db_operations as dbo  # noqa: E402

USER = SimpleNamespace(id=5, username="u", role_id=4)
ALL_TAGS = {"accessible_tags": {"*"}, "include_untagged": True, "default_tag_id": None}


def _visibility(customers, tags=ALL_TAGS, fn=dbo.alert_visibility_filters_for_user):
    with patch.object(dbo.customer_access_handler, "resolve_effective_customers", AsyncMock(return_value=customers)), patch.object(
        dbo.tag_access_handler,
        "build_alert_query_filters",
        AsyncMock(return_value=tags),
    ):
        return asyncio.run(fn(USER, AsyncMock()))


def _sql(filters):
    return " ".join(str(f) for f in filters)


def test_wildcard_customers_and_tags_filter_nothing():
    assert _visibility(["*"]) == []


def test_scoped_customers_filter_on_customer_code():
    filters = _visibility(["TENANT_A"])
    assert len(filters) == 1
    assert "customer_code IN" in _sql(filters)


def test_no_accessible_customer_sees_nothing():
    # An empty scope (e.g. a requested filter the user has no right to) must never
    # fall through to an unfiltered query.
    assert _visibility([]) is None


def test_tag_restricted_user_gets_a_tag_filter():
    filters = _visibility(["*"], {"accessible_tags": {3}, "include_untagged": False, "default_tag_id": None})
    assert "incident_management_alert_to_tag" in _sql(filters)


def test_untagged_alerts_included_when_allowed():
    filters = _visibility(["*"], {"accessible_tags": {3}, "include_untagged": True, "default_tag_id": None})
    assert _sql(filters).count("EXISTS") == 2  # tagged-with-allowed OR has-no-tag


def test_no_tags_and_no_untagged_sees_nothing():
    assert _visibility(["*"], {"accessible_tags": set(), "include_untagged": False, "default_tag_id": None}) is None


def test_portal_ai_surface_is_the_shared_definition_plus_the_switch():
    shared = _visibility(["TENANT_A"])
    portal = _visibility(["TENANT_A"], fn=portal_ai._alert_visibility_filters)
    assert _sql(portal).startswith(_sql(shared))
    assert "customer_portal_ai_report_settings" in _sql(portal[len(shared) :])


def test_portal_ai_surface_sees_nothing_when_the_user_sees_nothing():
    assert _visibility([], fn=portal_ai._alert_visibility_filters) is None
