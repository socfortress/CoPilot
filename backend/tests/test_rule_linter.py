"""Tests for the Graylog-only detection-rule L1 linter (editor + CI layer 1)."""
from __future__ import annotations

from app.integrations.copilot_searches.services.rule_linter import lint_graylog_query
from app.integrations.copilot_searches.services.rule_linter import lint_result
from app.integrations.copilot_searches.services.rule_linter import lint_rule_yaml

VALID = '''name: A New Trust Was Created To A Domain
id: 0255a820-e564-4e40-af2b-6ac61160335c
version: 1
schema_version: "1.0"
date: "2024-01-16"
author: Thomas Patzke
description: >
  Addition of domains is seldom and should be verified for legitimacy.
data_source:
  - Windows Security Event Log
how_to_implement: >
  Requires the Windows Security event log collected by the Wazuh agent.
known_false_positives: >
  Legitimate extension of domain structure.
response:
  risk_score: 50
  severity: medium
tags:
  asset_type: Endpoint
  mitre_attack_id:
    - T1098
  custom_tags:
    - trust
  product:
    - Wazuh
  security_domain: endpoint
graylog:
  query: data_win_system_eventID:"4706"
'''


def _codes(raw):
    return {f.code for f in lint_rule_yaml(raw)}


def test_valid_rule_is_clean():
    res = lint_result(VALID)
    assert res["valid"] is True, res["findings"]
    assert res["error_count"] == 0
    assert res["warning_count"] == 0


def test_unparseable_yaml():
    res = lint_result("name: [unbalanced\n")
    assert res["valid"] is False
    assert any(f["code"] == "YAML_PARSE" for f in res["findings"])


def test_missing_required_field():
    raw = VALID.replace("id: 0255a820-e564-4e40-af2b-6ac61160335c\n", "")
    codes = _codes(raw)
    assert "SCHEMA" in codes  # 'id' required


def test_forbidden_blocks_are_errors():
    raw = VALID + "search:\n  query:\n    match_all: {}\nparameters:\n  x: {}\n"
    codes = _codes(raw)
    assert "FORBIDDEN_BLOCK" in codes


def test_schema_version_must_be_quoted():
    raw = VALID.replace('schema_version: "1.0"', "schema_version: 1.0")
    assert "SCHEMA_VERSION_UNQUOTED" in _codes(raw)


def test_graylog_only_query():
    raw = VALID.replace(
        "graylog:\n  query: data_win_system_eventID:\"4706\"\n",
        'graylog:\n  query: data_win_system_eventID:"4706"\n  streams:\n    - abc\n',
    )
    assert "GRAYLOG_EXTRA_KEYS" in _codes(raw)


def test_aggregation_distinct_count_requires_field():
    raw = VALID + "aggregation:\n  enabled: true\n  function: distinct_count\n  threshold: 5\n  condition: '>'\n"
    assert "AGG_FIELD_REQUIRED" in _codes(raw)


def test_aggregation_count_forbids_field():
    raw = VALID + "aggregation:\n  enabled: true\n  function: count\n  field: user\n  threshold: 5\n  condition: '>'\n"
    assert "AGG_FIELD_FORBIDDEN" in _codes(raw)


def test_aggregation_must_follow_graylog():
    # aggregation placed BEFORE graylog
    raw = VALID.replace(
        "graylog:\n  query: data_win_system_eventID:\"4706\"\n",
        "aggregation:\n  enabled: true\n  function: count\n  threshold: 5\n  condition: '>'\n"
        'graylog:\n  query: data_win_system_eventID:"4706"\n',
    )
    assert "AGG_POSITION" in _codes(raw)


def test_bad_id_and_key_order_are_warnings():
    raw = "id: not-a-uuid\nname: X\nversion: 1\nschema_version: \"1.0\"\ndescription: y\ngraylog:\n  query: a:b\n"
    codes = _codes(raw)
    assert "ID_NOT_UUID" in codes
    assert "KEY_ORDER" in codes  # name after id, etc.


# ---- L3: Graylog query parse ----------------------------------------------
def _q_codes(query):
    return {f.code for f in lint_graylog_query(query)}


def test_query_valid():
    assert lint_graylog_query('data_win_system_eventID:"4706"') == []


def test_query_unbalanced_quotes():
    assert "GRAYLOG_QUERY_QUOTES" in _q_codes('foo:"bar')


def test_query_unbalanced_parens():
    assert "GRAYLOG_QUERY_PARENS" in _q_codes("(a:b OR c:d")


def test_query_unbalanced_regex():
    assert "GRAYLOG_QUERY_REGEX" in _q_codes("field:/abc")


def test_query_dangling_operator():
    assert "GRAYLOG_QUERY_DANGLING_OP" in _q_codes("a:b AND")


def test_query_leading_wildcard_is_warning_not_error():
    codes = _q_codes("field:/.*evil.*/")
    assert "GRAYLOG_QUERY_LEADING_WILDCARD" in codes
    assert "GRAYLOG_QUERY_REGEX" not in codes  # slashes are balanced


def test_query_empty():
    assert "GRAYLOG_QUERY_EMPTY" in _q_codes("   ")


def test_query_lint_runs_via_full_rule():
    raw = VALID.replace('query: data_win_system_eventID:"4706"', 'query: foo:"bar')
    assert "GRAYLOG_QUERY_QUOTES" in _codes(raw)


# --- L2: reference integrity (warnings only) --------------------------------
L2_BASE = '''name: L2 Test
id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
version: 1
schema_version: "1.0"
description: >
  test
response:
  message: >
    User $data_win_user$ did something from $missing_field$.
  risk_score: {score}
  severity: {severity}
  risk_objects:
    - field: data_win_user
      type: user
      score: 50
    - field: not_in_query
      type: host
tags:
  mitre_attack_id:
    - T1059.001
    - BOGUS123
graylog:
  query: data_win_system_eventID:"1" AND data_win_user:"x"
'''


def _codes(raw):
    return {f["code"] for f in lint_result(raw)["findings"]}


def test_l2_message_placeholder_flags_only_unused_fields():
    r = lint_result(L2_BASE.format(score=50, severity="medium"))
    msgs = [f for f in r["findings"] if f["code"] == "REF_MESSAGE_FIELD"]
    assert len(msgs) == 1 and "$missing_field$" in msgs[0]["message"]
    assert r["valid"]  # L2 findings are warnings, never errors


def test_l2_risk_object_flags_only_unused_fields():
    r = lint_result(L2_BASE.format(score=50, severity="medium"))
    objs = [f for f in r["findings"] if f["code"] == "REF_RISK_OBJECT"]
    assert len(objs) == 1 and "not_in_query" in objs[0]["message"]


def test_l2_mitre_format_flags_bogus_only():
    r = lint_result(L2_BASE.format(score=50, severity="medium"))
    mitre = [f for f in r["findings"] if f["code"] == "MITRE_ID_FORMAT"]
    assert len(mitre) == 1 and "BOGUS123" in mitre[0]["message"]


def test_l2_severity_score_mismatch():
    assert "SEVERITY_SCORE_MISMATCH" in _codes(L2_BASE.format(score=10, severity="critical"))
    assert "SEVERITY_SCORE_MISMATCH" not in _codes(L2_BASE.format(score=90, severity="critical"))


def test_l2_placeholder_satisfied_by_group_by():
    raw = L2_BASE.format(score=50, severity="medium") + '''aggregation:
  enabled: true
  function: count
  field: null
  group_by:
    - missing_field
  window: 10m
  threshold: 5
  condition: ">"
'''
    assert "REF_MESSAGE_FIELD" not in _codes(raw)
