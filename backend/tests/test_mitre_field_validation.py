"""Tests for MITRE alert-search input validation (GHSA-68c5-wpf3-9r62).

`mitre_field` lets a caller override which indexed field holds the MITRE technique id.
CoPilot interpolates that value by f-string into a Painless script
(`_build_mitre_search_query`, used by `GET /api/wazuh_manager/mitre/techniques/alerts`)
and into a Lucene `query_string` clause (`_build_mitre_alerts_query`, used by
`GET /api/wazuh_manager/mitre/techniques/{technique_id}/alerts`). A single quote in
`mitre_field` closes the Painless string literal and lets the caller append arbitrary
Painless; unescaped Lucene metacharacters do the equivalent in the query_string clause.

`technique_id`, the path parameter of the same alerts route, is interpolated by the same
f-string into the same `query_string` clause as `mitre_field` and is exposed to the exact
same Lucene breakout.

`_validate_mitre_field` constrains the field-name value to plain identifier characters
(`[A-Za-z0-9_.]`), and `_validate_technique_id` constrains the technique id to its real
format (`T` + 4 digits, optional `.NNN` sub-technique suffix, `T` optional), before either
sink uses either value, mirroring the identifier allow-list already used for Velociraptor
VQL interpolation (`app/connectors/velociraptor/utils/validation.py`, GHSA-5542-j2fc-gqjm).
Both run inside the query builders themselves, so they also cover any future caller of
`search_mitre_techniques_in_alerts` / `get_alerts_by_mitre_id` that does not go through
FastAPI's own `Query(..., pattern=...)` / `Path(..., pattern=...)` constraints on the routes.

Pure-function unit tests, no DB or Wazuh Indexer.

Run with: cd backend && python -m pytest tests/test_mitre_field_validation.py
"""

import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")
# app.connectors.wazuh_manager.services.mitre pulls in app.db.db_session transitively
# (via wazuh_indexer.utils.universal), which requires these at import time.
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "test-only-password-not-the-default")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "test-only-password-not-the-default")

from app.connectors.wazuh_manager.services.mitre import (  # noqa: E402
    _build_mitre_alerts_query,
)
from app.connectors.wazuh_manager.services.mitre import _build_mitre_search_query
from app.connectors.wazuh_manager.services.mitre import _validate_mitre_field
from app.connectors.wazuh_manager.services.mitre import _validate_technique_id


@pytest.mark.parametrize(
    "mitre_field",
    [
        "rule_mitre_id",  # the built-in default field
        "rule.mitre.id",  # a dotted default field
        "mitre.id",
        "Custom_Field.123",
    ],
)
def test_accepts_plain_field_names(mitre_field):
    assert _validate_mitre_field(mitre_field) == mitre_field


@pytest.mark.parametrize(
    "mitre_field",
    [
        "rule_mitre_id'].value); throw new Exception('x",  # Painless string-literal breakout
        "rule_mitre_id'] instanceof String ? '",
        "x'] == 'y",
        'x"] OR field:"y',  # Lucene query_string breakout
        "x OR 1=1",
        "x'",
        'x"',
        "x`",
        "x\\",
        "x\n",
        "x y",  # whitespace
        "",
        None,
    ],
)
def test_rejects_injection_and_malformed_field_names(mitre_field):
    with pytest.raises(HTTPException) as exc:
        _validate_mitre_field(mitre_field)
    assert exc.value.status_code == 400


def test_search_query_builder_rejects_unvalidated_field():
    """_build_mitre_search_query must reject the injection before it reaches script_source."""
    with pytest.raises(HTTPException) as exc:
        _build_mitre_search_query(
            time_range="now-24h",
            size=25,
            offset=0,
            additional_filters=None,
            index_pattern="wazuh-*",
            mitre_field="rule_mitre_id'].value); throw new Exception('x",
        )
    assert exc.value.status_code == 400


def test_search_query_builder_accepts_default_field():
    query = _build_mitre_search_query(
        time_range="now-24h",
        size=25,
        offset=0,
        additional_filters=None,
        index_pattern="wazuh-*",
        mitre_field="rule_mitre_id",
    )
    script_source = query["body"]["aggs"]["techniques"]["terms"]["script"]["source"]
    assert "doc['rule_mitre_id'].value" in script_source


def test_alerts_query_builder_rejects_unvalidated_field():
    """_build_mitre_alerts_query must reject the injection before it reaches query_string."""
    with pytest.raises(HTTPException) as exc:
        _build_mitre_alerts_query(
            technique_id="T1047",
            time_range="now-24h",
            size=25,
            offset=0,
            additional_filters=None,
            index_pattern="wazuh-*",
            mitre_field='x"] OR field:"y',
        )
    assert exc.value.status_code == 400


def test_alerts_query_builder_accepts_default_field():
    query = _build_mitre_alerts_query(
        technique_id="T1047",
        time_range="now-24h",
        size=25,
        offset=0,
        additional_filters=None,
        index_pattern="wazuh-*",
        mitre_field="rule_mitre_id",
    )
    should_clauses = query["body"]["query"]["bool"]["filter"][-1]["bool"]["should"]
    assert {"term": {"rule_mitre_id": "T1047"}} in should_clauses


@pytest.mark.parametrize(
    "technique_id",
    [
        "T1047",  # technique id with the "T" prefix
        "1047",  # bare-digit form, also documented on the route
        "T1003.004",  # sub-technique
        "1003.004",  # bare-digit sub-technique
    ],
)
def test_accepts_real_technique_ids(technique_id):
    assert _validate_technique_id(technique_id) == technique_id


@pytest.mark.parametrize(
    "technique_id",
    [
        'T1047" OR rule_mitre_id:*',  # Lucene query_string breakout (the reported gap)
        "T1047 OR 1=1",
        "T1047'",
        "T1047`",
        "T1047\\",
        "T1047\n",
        "T1047 ",  # trailing whitespace
        "T104",  # too few digits
        "T10470",  # too many digits
        "T1003.4",  # sub-technique suffix must be 3 digits
        "",
        None,
    ],
)
def test_rejects_injection_and_malformed_technique_ids(technique_id):
    with pytest.raises(HTTPException) as exc:
        _validate_technique_id(technique_id)
    assert exc.value.status_code == 400


def test_alerts_query_builder_rejects_unvalidated_technique_id():
    """_build_mitre_alerts_query must reject the injection before it reaches query_string."""
    with pytest.raises(HTTPException) as exc:
        _build_mitre_alerts_query(
            technique_id='T1047" OR rule_mitre_id:*',
            time_range="now-24h",
            size=25,
            offset=0,
            additional_filters=None,
            index_pattern="wazuh-*",
            mitre_field="rule_mitre_id",
        )
    assert exc.value.status_code == 400
