"""One imperfect stored row must not fail a whole list.

``GET /customers`` validated every row against the schema for *creating* a customer,
which requires the contact names, although the columns are nullable; ``GET
/auth/users`` validated every stored address as an email, and a reserved domain such
as ``.local`` is rejected. One such row turned the list into a 400 for everyone.
Responses now show what the row holds, while create and update keep their rules.

Run with: cd backend && python -m pytest tests/test_list_responses_tolerate_stored_data.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from pydantic import ValidationError  # noqa: E402

from app.auth.models.users import UserInput  # noqa: E402
from app.auth.schema.user import UserBaseResponse  # noqa: E402
from app.customers.schema.customers import CustomerMetaOut  # noqa: E402
from app.customers.schema.customers import CustomerMetaRequestBody  # noqa: E402
from app.customers.schema.customers import CustomerOut  # noqa: E402
from app.customers.schema.customers import CustomerRequestBody  # noqa: E402
from app.customers.schema.customers import CustomersResponse  # noqa: E402

# A customer inserted without contact names (manual SQL, an import, an older version).
NAMELESS = SimpleNamespace(customer_code="LEGACY", customer_name="Legacy Customer", contact_first_name=None, contact_last_name=None)
COMPLETE = SimpleNamespace(customer_code="ACME", customer_name="Acme", contact_first_name="Jane", contact_last_name="Doe")

META_WITH_NULLS = SimpleNamespace(
    customer_meta_graylog_index="idx",
    customer_meta_graylog_stream="stream",
    customer_meta_grafana_org_id="1",
    customer_meta_wazuh_group="LEGACY",
    customer_meta_index_retention=None,
    customer_meta_wazuh_registration_port=None,
    customer_meta_wazuh_log_ingestion_port=None,
    customer_meta_wazuh_api_port=None,
    customer_meta_wazuh_auth_password=None,
    customer_meta_portainer_stack_id=None,
)


def _user(id_, email):
    return {"id": id_, "username": f"user{id_}", "email": email, "role_id": 2, "role_name": "analyst"}


# ── customers ─────────────────────────────────────────────────────────────


def test_the_customers_list_returns_a_row_without_contact_names():
    from app.customers.routes import customers as route_module

    class _Result:
        def all(self):
            return [(COMPLETE, True), (NAMELESS, False)]

    session = MagicMock(execute=AsyncMock(return_value=_Result()))
    with patch.object(route_module, "apply_search_limit", lambda query, *a, **k: query), patch.object(
        route_module.customer_access_handler,
        "filter_query_by_customer_access",
        AsyncMock(side_effect=lambda user, sess, query, column: query),
    ):
        response = asyncio.run(
            route_module.get_customers(
                search_params=SimpleNamespace(search=None, limit=None),
                current_user=SimpleNamespace(id=1, role_id=1),
                session=session,
            ),
        )

    assert [c.customer_code for c in response.customers] == ["ACME", "LEGACY"]
    legacy = response.customers[1]
    assert (legacy.contact_first_name, legacy.contact_last_name, legacy.is_provisioned) == (None, None, False)


def test_customer_meta_with_null_columns_is_returned():
    meta = CustomerMetaOut.model_validate(META_WITH_NULLS)
    assert meta.customer_meta_wazuh_api_port is None and meta.customer_meta_graylog_index == "idx"


def test_the_old_request_schemas_are_what_used_to_fail():
    # Pins why the response schemas exist: the request ones reject these rows.
    with pytest.raises(ValidationError):
        CustomerRequestBody.model_validate(NAMELESS, from_attributes=True)
    with pytest.raises(ValidationError):
        CustomerMetaRequestBody.model_validate(META_WITH_NULLS, from_attributes=True)


def test_creating_a_customer_still_requires_the_contact_names():
    with pytest.raises(ValidationError) as exc:
        CustomerRequestBody(customer_code="NEW", customer_name="New")
    assert {error["loc"][0] for error in exc.value.errors()} == {"contact_first_name", "contact_last_name"}


def test_a_request_body_converts_to_the_response_shape():
    body = CustomerRequestBody(customer_code="NEW", customer_name="New", contact_first_name="A", contact_last_name="B")
    out = CustomerOut.model_validate(body)
    assert (out.customer_code, out.contact_first_name) == ("NEW", "A")
    assert CustomersResponse(customers=[out], success=True, message="").customers[0] == out


# ── users ─────────────────────────────────────────────────────────────────


def test_the_users_list_returns_an_internal_address():
    response = UserBaseResponse(
        users=[_user(1, "analyst@example.com"), _user(2, "admin@corp.local"), _user(3, "svc@localhost")],
        message="",
        success=True,
    )
    assert [u.email for u in response.users] == ["analyst@example.com", "admin@corp.local", "svc@localhost"]


def test_the_users_route_serves_them():
    from app.auth.routes import auth as auth_routes

    stored = [
        SimpleNamespace(
            id=2,
            username="admin2",
            email="admin@corp.local",
            role_id=1,
            role=SimpleNamespace(name="admin"),
            last_login_at=None,
        ),
    ]
    with patch.object(auth_routes, "select_all_users", AsyncMock(return_value=stored)):
        response = asyncio.run(auth_routes.get_users(search_params=SimpleNamespace(search=None, limit=None), session=MagicMock()))

    assert [u.email for u in response.users] == ["admin@corp.local"]


def test_creating_a_user_still_validates_the_address():
    with pytest.raises(ValidationError) as exc:
        UserInput(username="new", password="Str0ng!Passw0rd", email="new@corp.local")
    assert exc.value.errors()[0]["loc"] == ("email",)
