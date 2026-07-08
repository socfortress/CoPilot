import pytest

from app.connectors.wazuh_indexer.utils.customer_index import index_matches_customer


@pytest.mark.parametrize(
    "index_name,matchers,expected",
    [
        ("wazuh-copilot_37", ["copilot"], True),
        ("crowdstrike-acme_0", ["acme"], True),
        ("wazuh-other_1", ["copilot"], False),
        (None, ["copilot"], False),
        ("wazuh-copilot_37", [], False),
    ],
)
def test_index_matches_customer(index_name, matchers, expected):
    assert index_matches_customer(index_name, matchers) is expected
