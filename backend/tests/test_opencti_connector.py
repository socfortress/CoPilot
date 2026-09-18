"""OpenCTI connector: GraphQL transport, verification and service shaping.

**The trap this file exists for:** OpenCTI reports failure as HTTP 200. A bad
token answers

    200  {"errors": [{"message": "You must be logged in to do this.",
                      "extensions": {"code": "AUTH_REQUIRED"}}],
          "data": {"about": null}}

so "200 means healthy" would show a revoked token as a verified connector and
hand every caller a `data` full of nulls. Most of the transport tests pin that
any `errors` entry is a failure regardless of status.

Unit tests with stubbed HTTP — no network, no database.

Run with: cd backend && python -m pytest tests/test_opencti_connector.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.connectors.opencti.utils.universal as transport  # noqa: E402
from app.connectors.opencti.services import opencti as services  # noqa: E402
from app.connectors.opencti.services.queries import OBSERVABLE_LOOKUP_KEYS  # noqa: E402

ATTRS = {"connector_url": "http://opencti:8080", "connector_api_key": "octi-token"}

AUTH_REQUIRED = {
    "errors": [
        {
            "message": "You must be logged in to do this.",
            "extensions": {"code": "AUTH_REQUIRED", "data": {"http_status": 401}},
            "name": "AUTH_REQUIRED",
        },
    ],
    "data": {"about": None},
}


def _response(status=200, body=None):
    r = MagicMock()
    r.status_code = status
    if body is None:
        r.json.side_effect = ValueError("not json")
    else:
        r.json.return_value = body
    return r


def _client(*responses, raises=None):
    """An httpx.AsyncClient stand-in that answers each POST with the next response."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(side_effect=raises) if raises else AsyncMock(side_effect=list(responses))
    return client


def _run(coro, client, attrs=ATTRS):
    async def get_attributes(_name):
        return attrs

    with patch.object(transport.httpx, "AsyncClient", return_value=client), patch.object(transport, "_get_attributes", get_attributes):
        return asyncio.run(coro)


# ── URL handling ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "stored",
    ["http://opencti:8080", "http://opencti:8080/", "http://opencti:8080/graphql", "http://opencti:8080/graphql/", " http://opencti:8080 "],
)
def test_graphql_url_accepts_platform_or_endpoint(stored):
    assert transport.build_graphql_url(stored) == "http://opencti:8080/graphql"


# ── transport: the 200-with-errors trap ──────────────────────────────────────


def test_errors_on_http_200_are_a_failure():
    result = _run(transport.send_graphql_request("{ about { version } }"), _client(_response(200, AUTH_REQUIRED)))
    assert result["success"] is False
    assert "AUTH_REQUIRED" in result["message"]
    assert result["errors"] == AUTH_REQUIRED["errors"]
    # Partial data is handed back for callers that want it, but never as success.
    assert result["data"] == {"about": None}


def test_clean_response_is_success():
    body = {"data": {"about": {"version": "7.260907.0"}}}
    result = _run(transport.send_graphql_request("{ about { version } }"), _client(_response(200, body)))
    assert result == {"success": True, "message": "Successfully retrieved data", "data": body["data"], "errors": []}


def test_request_carries_bearer_token_and_variables():
    client = _client(_response(200, {"data": {}}))
    _run(transport.send_graphql_request("query($id: String!) { x(id: $id) }", {"id": "abc"}), client)
    kwargs = client.post.call_args.kwargs
    assert client.post.call_args.args[0] == "http://opencti:8080/graphql"
    assert kwargs["headers"]["Authorization"] == "Bearer octi-token"
    assert kwargs["json"] == {"query": "query($id: String!) { x(id: $id) }", "variables": {"id": "abc"}}


def test_http_error_without_graphql_errors_is_a_failure():
    result = _run(transport.send_graphql_request("{ x }"), _client(_response(502, {"data": None})))
    assert result["success"] is False
    assert "502" in result["message"]


def test_non_json_body_is_a_failure():
    result = _run(transport.send_graphql_request("{ x }"), _client(_response(502, None)))
    assert result["success"] is False
    assert "non-JSON" in result["message"]


def test_unreachable_server_is_a_failure_not_an_exception():
    result = _run(transport.send_graphql_request("{ x }"), _client(raises=httpx.ConnectError("refused")))
    assert result["success"] is False
    assert "Failed to reach OpenCTI" in result["message"]


def test_missing_connector_row():
    result = _run(transport.send_graphql_request("{ x }"), _client(), attrs=None)
    assert result["success"] is False
    assert "No OpenCTI connector" in result["message"]


# ── verification (the Connectors page Verify button) ─────────────────────────


def test_verify_rejects_bad_token_despite_http_200():
    result = _run(transport.verify_opencti_credentials(ATTRS), _client(_response(200, AUTH_REQUIRED)))
    assert result["connectionSuccessful"] is False
    assert "AUTH_REQUIRED" in result["message"]


def test_verify_success_names_version_and_user():
    body = {"data": {"about": {"version": "7.260907.0"}, "me": {"name": "admin", "user_email": "a@b.c"}}}
    result = _run(transport.verify_opencti_credentials(ATTRS), _client(_response(200, body)))
    assert result["connectionSuccessful"] is True
    assert "7.260907.0" in result["message"] and "admin" in result["message"]


def test_verify_without_url_does_not_call_out():
    client = _client()
    result = _run(transport.verify_opencti_credentials({"connector_url": "", "connector_api_key": "k"}), client)
    assert result == {"connectionSuccessful": False, "message": "No OpenCTI URL is configured"}
    client.post.assert_not_called()


def test_opencti_is_registered_for_verify():
    from app.connectors.services import OpenCTIService
    from app.connectors.services import get_connector_service

    assert get_connector_service("OpenCTI") is OpenCTIService


# ── pagination ───────────────────────────────────────────────────────────────

PAGED_QUERY = "query($first: Int, $after: ID) { reports(first: $first, after: $after) { pageInfo { hasNextPage endCursor globalCount } edges { node { id } } } }"


def _page(ids, has_next, cursor, total=5):
    return _response(
        200,
        {
            "data": {
                "reports": {
                    "pageInfo": {"hasNextPage": has_next, "endCursor": cursor, "globalCount": total},
                    "edges": [{"node": {"id": i}} for i in ids],
                },
            },
        },
    )


def test_paginate_follows_cursor_to_the_end():
    client = _client(_page(["a", "b"], True, "c1"), _page(["c", "d"], True, "c2"), _page(["e"], False, ""))
    result = _run(transport.paginate_graphql(PAGED_QUERY, ["reports"], page_size=2), client)
    assert result["success"] is True
    assert [n["id"] for n in result["data"]] == ["a", "b", "c", "d", "e"]
    assert result["global_count"] == 5
    sent = [call.kwargs["json"]["variables"] for call in client.post.call_args_list]
    assert sent == [{"first": 2, "after": None}, {"first": 2, "after": "c1"}, {"first": 2, "after": "c2"}]


def test_paginate_stops_at_max_items_and_shrinks_the_last_page():
    client = _client(_page(["a", "b"], True, "c1"), _page(["c"], True, "c2"))
    result = _run(transport.paginate_graphql(PAGED_QUERY, ["reports"], page_size=2, max_items=3), client)
    assert [n["id"] for n in result["data"]] == ["a", "b", "c"]
    assert client.post.call_args_list[1].kwargs["json"]["variables"]["first"] == 1


def test_paginate_stops_when_the_cursor_does_not_advance():
    client = _client(_page(["a"], True, "same"), _page(["b"], True, "same"), _page(["never"], False, ""))
    result = _run(transport.paginate_graphql(PAGED_QUERY, ["reports"], page_size=1), client)
    assert [n["id"] for n in result["data"]] == ["a", "b"]
    assert client.post.call_count == 2


def test_paginate_mid_walk_failure_returns_what_it_had():
    client = _client(_page(["a", "b"], True, "c1"), _response(200, AUTH_REQUIRED))
    result = _run(transport.paginate_graphql(PAGED_QUERY, ["reports"], page_size=2), client)
    assert result["success"] is False
    assert [n["id"] for n in result["data"]] == ["a", "b"]


def test_paginate_wrong_connection_path_is_a_failure():
    client = _client(_page(["a"], False, ""))
    result = _run(transport.paginate_graphql(PAGED_QUERY, ["indicators"]), client)
    assert result["success"] is False
    assert "indicators" in result["message"]


# ── query documents ──────────────────────────────────────────────────────────


def test_every_query_defines_exactly_the_fragments_it_spreads():
    """OpenCTI rejects a document with an unused or undefined fragment, and only at request time."""
    import re

    from app.connectors.opencti.services import queries

    documents = {name: value for name, value in vars(queries).items() if name.endswith("_QUERY")}
    assert documents
    for name, document in documents.items():
        defined = set(re.findall(r"fragment\s+(\w+)\s+on", document))
        spread = set(re.findall(r"\.\.\.(\w+)", document)) - {"on"}
        assert defined == spread, f"{name}: defines {sorted(defined)} but spreads {sorted(spread)}"


# ── services ─────────────────────────────────────────────────────────────────


def test_lookup_matches_value_and_every_hash_in_one_filter():
    client = _client(_response(200, {"data": {"stixCyberObservables": {"pageInfo": {"globalCount": 0}, "edges": []}}}))
    result = _run(services.lookup_observable("  8.8.8.8 \n"), client)
    assert result.found is False and result.value == "8.8.8.8"
    [item] = client.post.call_args.kwargs["json"]["variables"]["filters"]["filters"]
    assert item["key"] == OBSERVABLE_LOOKUP_KEYS and item["values"] == ["8.8.8.8"] and item["mode"] == "or"


def test_lookup_rejects_a_blank_value_without_calling_out():
    """`min_length` on the route passes "   "; stripped, it must not become an empty lookup."""
    from fastapi import HTTPException

    client = _client()
    with pytest.raises(HTTPException) as exc:
        _run(services.lookup_observable("   "), client)
    assert exc.value.status_code == 400
    client.post.assert_not_called()


def test_lookup_flattens_the_graphql_shape():
    node = {
        "id": "obs-1",
        "standard_id": "file--1",
        "entity_type": "StixFile",
        "createdBy": None,
        "objectLabel": [{"value": "malware", "color": "#f00"}, None],
        "objectMarking": [{"definition": "TLP:CLEAR"}],
        "observable_value": "abc123",
        "x_opencti_score": 80,
        "name": "evil.exe",
        "hashes": [{"algorithm": "SHA-256", "hash": "abc123"}],
        "indicators": {
            "pageInfo": {"globalCount": 3},
            "edges": [{"node": {"id": "ind-1", "entity_type": "Indicator", "name": "abc123", "x_opencti_score": 80, "revoked": False}}],
        },
        "reports": None,
    }
    body = {"data": {"stixCyberObservables": {"pageInfo": {"globalCount": 1}, "edges": [{"node": node}]}}}
    result = _run(services.lookup_observable("ABC123"), _client(_response(200, body)))
    [obs] = result.observables
    assert result.found is True and result.total == 1
    assert obs.value == "abc123" and obs.file_name == "evil.exe" and obs.score == 80
    assert obs.created_by is None and [label.value for label in obs.labels] == ["malware"] and obs.markings == ["TLP:CLEAR"]
    assert obs.indicators_count == 3 and obs.indicators[0].score == 80
    assert obs.reports == [] and obs.reports_count == 0


def test_graphql_failure_surfaces_as_http_error():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _run(services.get_platform_info(), _client(_response(200, AUTH_REQUIRED)))
    assert exc.value.status_code == 500
    assert "AUTH_REQUIRED" in exc.value.detail


def test_unknown_entity_is_404():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _run(services.get_entity("nope"), _client(_response(200, {"data": {"stixCoreObject": None}})))
    assert exc.value.status_code == 404


def test_indicator_filters_are_only_sent_when_asked_for():
    empty = {"data": {"indicators": {"pageInfo": {"globalCount": 0, "hasNextPage": False, "endCursor": ""}, "edges": []}}}

    client = _client(_response(200, empty))
    result = _run(services.search_indicators(), client)
    assert client.post.call_args.kwargs["json"]["variables"]["filters"] is None
    assert result.page_info.end_cursor is None

    client = _client(_response(200, empty))
    _run(services.search_indicators(min_score=80, main_observable_type="IPv4-Addr"), client)
    filters = client.post.call_args.kwargs["json"]["variables"]["filters"]["filters"]
    assert {(f["key"][0], f["operator"]) for f in filters} == {("x_opencti_score", "gte"), ("x_opencti_main_observable_type", "eq")}


# ── seeding ──────────────────────────────────────────────────────────────────


def test_seed_never_inserts_a_null_url(monkeypatch):
    """`connectors.connector_url` is NOT NULL; an upgrade without OPENCTI_URL must still boot."""
    from app.db.db_populate import load_connector_data

    monkeypatch.delenv("OPENCTI_URL", raising=False)
    data = load_connector_data("OpenCTI", "7", "api_key", "desc")
    assert data["connector_url"] == ""
    assert data["connector_accepts_api_key"] is True


def test_seed_list_includes_opencti():
    from app.db.db_populate import get_connectors_list

    assert "OpenCTI" in {c["connector_name"] for c in get_connectors_list()}


# ── availability (frontend gating, #1145) ────────────────────────────────────


def _availability(row):
    async def get_connector_info_from_db(_name, _session):
        return row

    class _Session:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *exc):
            return False

    with patch.object(services, "get_connector_info_from_db", get_connector_info_from_db), patch.object(
        services,
        "get_db_session",
        lambda: _Session(),
    ):
        return asyncio.run(services.get_availability())


@pytest.mark.parametrize(
    ("row", "configured", "verified"),
    [
        (None, False, False),
        ({"connector_url": "", "connector_api_key": "k", "connector_verified": True}, False, False),
        ({"connector_url": "http://opencti:8080", "connector_api_key": None, "connector_verified": True}, False, False),
        ({"connector_url": "http://opencti:8080", "connector_api_key": "k", "connector_verified": False}, True, False),
        ({"connector_url": "http://opencti:8080", "connector_api_key": "k", "connector_verified": True}, True, True),
    ],
)
def test_availability_reflects_the_connector_row(row, configured, verified):
    result = _availability(row)
    assert (result.configured, result.verified) == (configured, verified)


def test_availability_never_returns_credentials():
    row = {"connector_url": "http://opencti:8080", "connector_api_key": "secret-token", "connector_verified": True}
    assert "secret-token" not in _availability(row).model_dump_json()


@pytest.mark.parametrize("stored", ["http://opencti:8080", "http://opencti:8080/", "http://opencti:8080/graphql"])
def test_availability_platform_url_is_the_web_address(stored):
    row = {"connector_url": stored, "connector_api_key": "k", "connector_verified": True}
    assert _availability(row).platform_url == "http://opencti:8080"


def test_availability_hides_platform_url_until_verified():
    row = {"connector_url": "http://opencti:8080", "connector_api_key": "k", "connector_verified": False}
    assert _availability(row).platform_url is None


# ── batch lookup (inline alert IoC badges, #1146) ────────────────────────────


def _observable_node(id_, value=None, hashes=None, entity_type="IPv4-Addr"):
    return {
        "id": id_,
        "entity_type": entity_type,
        "observable_value": value,
        "hashes": [{"algorithm": "SHA-256", "hash": h} for h in hashes or []],
        "objectLabel": [],
        "objectMarking": [],
    }


def _connection(*nodes, total=None):
    return {
        "data": {
            "stixCyberObservables": {
                "pageInfo": {"globalCount": len(nodes) if total is None else total},
                "edges": [{"node": n} for n in nodes],
            },
        },
    }


def test_batch_request_strips_dedupes_and_keeps_order():
    from app.connectors.opencti.schema.opencti import OpenCTIBatchLookupRequest

    request = OpenCTIBatchLookupRequest(values=[" b.com ", "A.com", "", "a.COM", "b.com", "c.com"])
    assert request.values == ["b.com", "A.com", "c.com"]


@pytest.mark.parametrize("values", [[], ["", "  "], ["x"] * 101, ["x" * 2049]])
def test_batch_request_rejects_bad_input(values):
    from pydantic import ValidationError

    from app.connectors.opencti.schema.opencti import OpenCTIBatchLookupRequest

    with pytest.raises(ValidationError):
        OpenCTIBatchLookupRequest(values=values)


def test_batch_lookup_is_one_query_with_every_value():
    client = _client(_response(200, _connection()))
    _run(services.lookup_observables(["1.2.3.4", "evil.com", "abc123"]), client)
    assert client.post.call_count == 1
    [item] = client.post.call_args.kwargs["json"]["variables"]["filters"]["filters"]
    assert item["values"] == ["1.2.3.4", "evil.com", "abc123"] and item["key"] == OBSERVABLE_LOOKUP_KEYS


def test_batch_lookup_maps_observables_back_to_values():
    """OpenCTI doesn't say which value each observable matched; hashes and case must still map back."""
    body = _connection(
        _observable_node("ip", value="1.2.3.4"),
        _observable_node("file", value="aaa", hashes=["aaa", "bbb"], entity_type="StixFile"),
        _observable_node("dom", value="evil.com", entity_type="Domain-Name"),
        _observable_node("host", value="evil.com", entity_type="Hostname"),
    )
    result = _run(services.lookup_observables(["1.2.3.4", "BBB", "Evil.com", "8.8.8.8"]), _client(_response(200, body)))
    by_value = {r.value: [o.id for o in r.observables] for r in result.results}
    assert [r.value for r in result.results] == ["1.2.3.4", "BBB", "Evil.com", "8.8.8.8"]
    assert by_value == {"1.2.3.4": ["ip"], "BBB": ["file"], "Evil.com": ["dom", "host"], "8.8.8.8": []}
    assert [r.found for r in result.results] == [True, True, True, False]
    assert result.truncated is False
    assert result.message == "3 of 4 values found in OpenCTI"


def test_batch_lookup_flags_a_truncated_answer():
    body = _connection(_observable_node("ip", value="1.2.3.4"), total=900)
    assert _run(services.lookup_observables(["1.2.3.4"]), _client(_response(200, body))).truncated is True


def test_batch_lookup_sizes_the_page_to_the_request():
    client = _client(_response(200, _connection()))
    _run(services.lookup_observables(["v"] * 1), client)
    assert client.post.call_args.kwargs["json"]["variables"]["first"] == 50

    client = _client(_response(200, _connection()))
    _run(services.lookup_observables([f"v{i}" for i in range(100)]), client)
    assert client.post.call_args.kwargs["json"]["variables"]["first"] == services.BATCH_MAX_OBSERVABLES
