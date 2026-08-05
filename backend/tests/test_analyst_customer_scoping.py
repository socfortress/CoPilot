"""Regression tests for #1050 — assigning customers to an analyst had no effect.

``CustomerAccessHandler.get_user_accessible_customers`` returned the ``["*"]``
wildcard for every analyst, so the rows written by *Users -> Assign Customer*
were stored and then ignored: an analyst assigned to one customer still saw all
of them.

The fix makes assignments authoritative for analysts, while keeping an analyst
with *no* assignments deployment-wide so upgrading a deployment does not strip
access from every existing analyst.

These are unit tests against the handler with a mocked session; no real DB.

Run with: cd backend && python -m pytest tests/test_analyst_customer_scoping.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.auth.models.users import RoleEnum  # noqa: E402
from app.middleware.customer_access import CustomerAccessHandler  # noqa: E402

ASSIGNED = "TENANT_A"
FOREIGN = "TENANT_B"


def _user(role_id):
    return SimpleNamespace(id=7, username="user", role_id=role_id)


def _session(assigned_codes):
    """AsyncSession whose single query returns ``assigned_codes``."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = assigned_codes
    session.execute = AsyncMock(return_value=result)
    return session


def _accessible(role_id, assigned_codes):
    session = _session(assigned_codes)
    codes = asyncio.run(CustomerAccessHandler().get_user_accessible_customers(_user(role_id), session))
    return codes, session


# ── the bug: an assigned analyst must lose the wildcard ───────────────────


def test_analyst_with_assignments_is_scoped_to_them():
    codes, _ = _accessible(RoleEnum.analyst, [ASSIGNED])
    assert codes == [ASSIGNED]
    assert "*" not in codes


def test_analyst_without_assignments_keeps_deployment_wide_access():
    # backwards compatibility: no deployment has assigned analysts before this change
    codes, _ = _accessible(RoleEnum.analyst, [])
    assert codes == ["*"]


def test_admin_ignores_assignments_entirely():
    codes, session = _accessible(RoleEnum.admin, [ASSIGNED])
    assert codes == ["*"]
    # an admin must not be scopeable by accident, so the table is never consulted
    session.execute.assert_not_called()


def test_customer_user_without_assignments_gets_nothing():
    # a portal user must never fall back to the wildcard
    codes, _ = _accessible(RoleEnum.customer_user, [])
    assert codes == []


def test_customer_user_with_assignments_is_unchanged():
    codes, _ = _accessible(RoleEnum.customer_user, [ASSIGNED])
    assert codes == [ASSIGNED]


def test_scheduler_role_has_no_access():
    codes, _ = _accessible(RoleEnum.scheduler, [ASSIGNED])
    assert codes == []


# ── the consequences for callers ─────────────────────────────────────────


def test_scoped_analyst_is_denied_a_foreign_customer():
    handler = CustomerAccessHandler()
    allowed = asyncio.run(handler.check_customer_access(_user(RoleEnum.analyst), FOREIGN, _session([ASSIGNED])))
    assert allowed is False


def test_scoped_analyst_is_allowed_their_own_customer():
    handler = CustomerAccessHandler()
    allowed = asyncio.run(handler.check_customer_access(_user(RoleEnum.analyst), ASSIGNED, _session([ASSIGNED])))
    assert allowed is True


def test_unassigned_analyst_still_reaches_every_customer():
    handler = CustomerAccessHandler()
    allowed = asyncio.run(handler.check_customer_access(_user(RoleEnum.analyst), FOREIGN, _session([])))
    assert allowed is True


def test_enforce_customer_access_raises_403_for_scoped_analyst():
    from fastapi import HTTPException

    handler = CustomerAccessHandler()
    try:
        asyncio.run(handler.enforce_customer_access(_user(RoleEnum.analyst), FOREIGN, _session([ASSIGNED])))
    except HTTPException as exc:
        assert exc.status_code == 403
        assert FOREIGN in exc.detail
    else:
        raise AssertionError("expected a 403 for a customer the analyst is not assigned to")


def test_requested_subset_cannot_widen_a_scoped_analyst():
    # a stale/hostile customer_code from the client must not escape the assignment
    handler = CustomerAccessHandler()
    effective = asyncio.run(
        handler.resolve_effective_customers(
            _user(RoleEnum.analyst),
            [ASSIGNED, FOREIGN],
            _session([ASSIGNED]),
        ),
    )
    assert effective == [ASSIGNED]


def test_query_is_narrowed_for_a_scoped_analyst():
    handler = CustomerAccessHandler()
    base_query = MagicMock()
    column = MagicMock()

    asyncio.run(
        handler.filter_query_by_customer_access(
            _user(RoleEnum.analyst),
            _session([ASSIGNED]),
            base_query,
            column,
        ),
    )

    column.in_.assert_called_once_with([ASSIGNED])
    base_query.where.assert_called_once()


def test_unfiltered_listings_are_bounded_by_scope_but_keep_shared_rows():
    """The aggregate case: no customer_code asked for.

    A scoped caller must get their tenants' rows plus the explicitly-shared ones
    (``customer_code IS NULL``), never another tenant's. Asserted on the SQL the
    services build, since the e2e that exercises them needs a live MySQL.
    """
    from app.notifications.services.templates import list_templates
    from app.siem.services.custom_dashboards import list_custom_dashboards

    for service, kwargs in (
        (list_custom_dashboards, {"customer_code": None, "accessible_customers": [ASSIGNED]}),
        (list_templates, {"customer_code": None, "accessible_customers": [ASSIGNED]}),
    ):
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)

        if service is list_custom_dashboards:
            asyncio.run(service(kwargs["customer_code"], session, accessible_customers=kwargs["accessible_customers"]))
        else:
            asyncio.run(service(session, **kwargs))

        sql = str(session.execute.call_args.args[0])
        assert "IN (" in sql, f"{service.__name__} does not bound the listing to the caller's tenants"
        assert "IS NULL" in sql, f"{service.__name__} drops the globally-shared rows"


def test_unfiltered_listings_are_untouched_for_deployment_wide_callers():
    from app.siem.services.custom_dashboards import list_custom_dashboards

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)

    asyncio.run(list_custom_dashboards(None, session, accessible_customers=["*"]))

    sql = str(session.execute.call_args.args[0])
    assert "WHERE" not in sql


def test_optional_code_dependency_enforces_a_supplied_code():
    from fastapi import HTTPException

    from app.middleware.customer_access import verify_optional_customer_code_access

    try:
        asyncio.run(
            verify_optional_customer_code_access(
                customer_code=FOREIGN,
                current_user=_user(RoleEnum.analyst),
                session=_session([ASSIGNED]),
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("a scoped analyst must not read another tenant by naming it in the query")


def test_optional_code_dependency_passes_through_when_absent():
    # no code means "everything the caller may see" — narrowing that is the service's job
    from app.middleware.customer_access import verify_optional_customer_code_access

    result = asyncio.run(
        verify_optional_customer_code_access(
            customer_code=None,
            current_user=_user(RoleEnum.analyst),
            session=_session([ASSIGNED]),
        ),
    )
    assert result is None


def test_query_is_untouched_for_an_unassigned_analyst():
    handler = CustomerAccessHandler()
    base_query = MagicMock()
    column = MagicMock()

    returned = asyncio.run(
        handler.filter_query_by_customer_access(
            _user(RoleEnum.analyst),
            _session([]),
            base_query,
            column,
        ),
    )

    assert returned is base_query
    base_query.where.assert_not_called()
