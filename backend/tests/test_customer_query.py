from unittest.mock import MagicMock

from app.middleware.customer_query import customer_codes_query


def test_customer_codes_query_repeated_params():
    request = MagicMock()
    request.query_params = MagicMock()
    request.query_params.getlist.return_value = []

    assert customer_codes_query(request, ["test", "demo"]) == ["test", "demo"]


def test_customer_codes_query_bracket_params():
    request = MagicMock()
    request.query_params = MagicMock()
    request.query_params.getlist.return_value = ["test"]

    assert customer_codes_query(request, None) == ["test"]


def test_customer_codes_query_empty():
    request = MagicMock()
    request.query_params = MagicMock()
    request.query_params.getlist.return_value = []

    assert customer_codes_query(request, None) is None
