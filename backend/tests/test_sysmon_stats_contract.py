"""The report contract v1 CoPilot checks its reports with (contract_v1.py, contract_v1_rules.py: vendored from sysmon-sync).

(a) Unit tests of the vendored validator.
(b) When SYSMON_SYNC_DIR names a sysmon-sync checkout: its app/reports is loaded as a synthetic package (both repositories'
    top-level package is ``app``), its constants must equal the vendored ones, and its own validator must accept every
    golden report and 200 randomized reports CoPilot builds from the golden redaction inputs: never a refusal, never a
    dropped pattern. Otherwise those tests are skipped ("vendored copy only").

Run with: cd backend && SYSMON_SYNC_DIR=/path/to/sysmon-sync python -m pytest tests/test_sysmon_stats_contract.py
"""
import importlib
import importlib.util
import json
import os
import random
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.services.sysmon_stats import contract_v1 as c  # noqa: E402
from app.active_response.services.sysmon_stats import contract_v1_rules as rules  # noqa: E402
from app.active_response.services.sysmon_stats import report as rep  # noqa: E402
from app.active_response.services.sysmon_stats.queries import RawPattern  # noqa: E402
from app.active_response.services.sysmon_stats.redaction import (  # noqa: E402
    build_context,
)

FIXTURES = Path(__file__).parent / "fixtures" / "sysmon_stats"
CUST = "cust_" + "c" * 32


def base(patterns):
    return {
        "format": "socfortress-sysmon-report/1",
        "customer": CUST,
        "week": "2026-W47",
        "config": 56,
        "endpoints": 40,
        "truncated": False,
        "patterns": patterns,
    }


def dns(**kw):
    p = {
        "event_id": 22,
        "fields": {"Image": "C:\\Program Files\\Fabrikam\\agent.exe", "QueryName": "t.fabrikam-example.com"},
        "events": 5,
        "endpoints": 3,
        "days": 1,
    }
    p.update(kw)
    return p


# ── (a) the vendored validator ──────────────────────────────────────────────


def test_a_valid_report_is_accepted():
    parsed = c.validate_report(
        base(
            [
                dns(),
                dns(
                    fields={
                        "Image": "C:\\Program Files\\Fabrikam\\agent.exe",
                        "QueryName": "u.fabrikam-example.com",
                        "User": "NT AUTHORITY\\SYSTEM",
                    },
                ),
            ],
        ),
    )
    assert len(parsed.accepted) == 2 and parsed.rejected == []


@pytest.mark.parametrize(
    "doc,reason",
    [
        ({**base([]), "extra": 1}, "malformed"),
        ({**base([]), "format": "x"}, "format"),
        (base([dns()] * 71), "too-many-patterns"),
        (
            base([dns(fields={"Image": "a", "QueryName": "b", "User": "-", "QueryStatus": "0", "RuleName": "x", "ProcessId": "1"})]),
            "too-many-fields",
        ),
        (base([dns(fields={"Image": "C:\\Users\\jdoe\\x.exe", "QueryName": "t.example.com"})]), "identity-leak"),
        (base([dns(fields={"Image": "a", "QueryName": "t.example.com", "CommandLine": "x"})]), "command-line"),
        (base([dns(fields={"Image": "a", "QueryName": "t.example.com", "Hashes": "x"})]), "field-not-allowed"),
        (base([dns(), dns()]), "duplicate-pattern"),
        (base([dns(endpoints=41)]), "malformed"),
        (base([dns(rule_name="see \\\\FS01\\share")]), "identity-leak"),
    ],
)
def test_refusals(doc, reason):
    with pytest.raises(c.ReportRefused) as raised:
        c.validate_report(doc)
    assert raised.value.reason == reason


def test_drops_are_per_pattern():
    parsed = c.validate_report(
        base(
            [
                dns(event_id=4),
                dns(fields={"Image": "C:\\x*.exe", "QueryName": "t.example.com"}),
                dns(fields={"Image": "a", "QueryName": "\u00e9.example.com"}),
            ],
        ),
    )
    assert [p.reason for p in parsed.rejected] == ["event-not-accepted", "wildcard", "non-ascii-dns"]


def test_the_week_rules():
    assert c.week_accepted(date(2026, 11, 16), date(2026, 11, 24), 2)
    assert c.week_accepted(date(2026, 11, 9), date(2026, 11, 24), 2)
    assert not c.week_accepted(date(2026, 11, 2), date(2026, 11, 24), 2)
    assert not c.week_accepted(date(2026, 11, 23), date(2026, 11, 24), 2)
    assert c.last_completed_sunday(date(2026, 11, 23)) == date(2026, 11, 22)


# ── (b) against a sysmon-sync checkout ──────────────────────────────────────

SYSMON_SYNC_DIR = os.environ.get("SYSMON_SYNC_DIR", "").strip()
needs_service = pytest.mark.skipif(not SYSMON_SYNC_DIR, reason="vendored copy only (set SYSMON_SYNC_DIR)")


def service_reports():
    """sysmon-sync's app/reports as the package _sysmon_sync_reports (its modules use relative imports only)."""
    if "_sysmon_sync_reports" in sys.modules:
        return importlib.import_module("_sysmon_sync_reports.contract"), importlib.import_module("_sysmon_sync_reports.cka_rules")
    root = Path(SYSMON_SYNC_DIR) / "app" / "reports"
    spec = importlib.util.spec_from_file_location("_sysmon_sync_reports", root / "__init__.py", submodule_search_locations=[str(root)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sysmon_sync_reports"] = module
    spec.loader.exec_module(module)
    return importlib.import_module("_sysmon_sync_reports.contract"), importlib.import_module("_sysmon_sync_reports.cka_rules")


@needs_service
def test_the_vendored_constants_are_the_services():
    contract, cka = service_reports()
    package = sys.modules["_sysmon_sync_reports"]
    assert {k: asdict(v) for k, v in c.EVENTS.items()} == {k: asdict(v) for k, v in contract.EVENTS.items()}
    for name in (
        "NEVER_FIELDS",
        "ALLOW_LISTED",
        "TOP_KEYS",
        "PATTERN_REQUIRED",
        "PATTERN_KEYS",
        "COMMAND_LINE_FIELDS",
        "REFUSAL_ORDER",
        "DROP_REASONS",
        "VALUE_REASON_ORDER",
        "REPORT_FORMAT",
        "WITHDRAW_FORMAT",
        "PATTERN_KEY_LABEL",
        "MAX_CONFIG",
        "MAX_REPORT_ENDPOINTS",
        "MAX_PATTERN_EVENTS",
        "CONFIG_WORDS",
    ):
        assert getattr(c, name) == getattr(contract, name), name
    for name in ("CUSTOMER_RE", "WEEK_RE", "EMAIL_RE", "ONEDRIVE_RE"):
        assert getattr(c, name).pattern == getattr(contract, name).pattern, name
    for name in ("MAX_PATTERNS", "MAX_FIELDS_PER_PATTERN", "MAX_REFUSAL_LISTED", "MAX_REPORT_BYTES", "MAX_WITHDRAW_BYTES"):
        assert getattr(c, name) == getattr(package, name), name
    for name in (
        "REDACTION",
        "PLACEHOLDERS",
        "TOKEN",
        "CONFUSABLES",
        "MAX_VALUE_LEN",
        "MAX_RULENAME_LEN",
        "MAX_COMMAND_LINE_LEN",
        "BAD_CATEGORIES",
        "SERVICE_HIVES",
        "REGISTRY_SERVICE_HIVES",
        "WELL_KNOWN_DOMAINS",
        "WELL_KNOWN_ACCOUNTS",
        "USER_FIELDS",
        "PATH_FIELDS",
        "DNS_FIELDS",
        "UNSTABLE_FIELDS",
        "REGISTRY_KEY_FIELDS",
        "_PROBLEM_REASONS",
        "CKA_COMMIT",
        "SID_PATTERN",
    ):
        assert getattr(rules, name) == getattr(cka, name), name
    for name in ("USER_DIR_RE", "UNC_ANY_RE", "SID_RE", "HKU_HIVE_RE", "PLACEHOLDER_LIKE", "TEMPLATE_TOKEN_LIKE", "ENV_VAR_RE"):
        assert getattr(rules, name).pattern == getattr(cka, name).pattern, name


def _golden_reports():
    yield json.loads((FIXTURES / "expected_report.json").read_text())


def _corpus():
    """Raw patterns from the golden redaction inputs: each value in the field it was written for."""
    data = json.loads((FIXTURES / "redaction_cases.json").read_text(encoding="utf-8"))
    agent = "C:\\\\Program Files\\\\Fabrikam\\\\agent.exe"
    out = []
    for case in data["cases"]:
        field, raw = case["field"], case["raw"]
        if field in ("TargetFilename",):
            out.append(RawPattern(11, {"Image": agent, "TargetFilename": raw}, 1, 3, 1, {"User": ["NT AUTHORITY\\\\SYSTEM"]}, ["-"]))
        elif field == "Image":
            out.append(RawPattern(1, {"Image": raw, "ParentImage": "C:\\\\Windows\\\\explorer.exe"}, 1, 3, 1, {}, None))
        elif field == "TargetObject":
            out.append(RawPattern(13, {"Image": agent, "TargetObject": raw}, 1, 3, 1, {}, None))
        elif field in ("QueryName",):
            out.append(RawPattern(22, {"Image": agent, "QueryName": raw}, 1, 3, 1, {}, None))
        elif field == "DestinationHostname":
            out.append(RawPattern(3, {"Image": agent, "DestinationHostname": raw, "DestinationPort": "443"}, 1, 3, 1, {}, None))
        elif field == "PipeName":
            out.append(RawPattern(17, {"Image": agent, "PipeName": raw}, 1, 3, 1, {}, None))
        elif field in ("User", "SourceUser", "TargetUser"):
            out.append(
                RawPattern(
                    10,
                    {"SourceImage": agent, "TargetImage": "C:\\\\Windows\\\\System32\\\\lsass.exe", "GrantedAccess": "0x1010"},
                    1,
                    3,
                    1,
                    {"SourceUser": [raw], "TargetUser": ["NT AUTHORITY\\\\SYSTEM"]},
                    None,
                ),
            )
    return data["default_ctx"], out


@needs_service
def test_the_services_validator_accepts_every_report_copilot_builds():
    contract, _ = service_reports()
    for doc in _golden_reports():
        parsed = contract.validate_report(doc)
        assert parsed.rejected == []
    ctx_spec, corpus = _corpus()
    rnd = random.Random(1234)
    built_reports = 0
    for i in range(200):
        sample = []
        for p in rnd.sample(corpus, k=rnd.randint(1, min(40, len(corpus)))):
            sample.append(
                RawPattern(
                    p.eid,
                    dict(p.key),
                    rnd.randint(1, 10**6),
                    rnd.randint(3, 40),
                    rnd.randint(1, 127),
                    dict(p.details),
                    p.rule_names,
                ),
            )
        built = rep.build_report(
            customer=CUST,
            week="2026-W47",
            config=rnd.choice([56, "customized", "unknown"]),
            endpoints=40,
            raw_patterns=sample,
            ctx=build_context(**ctx_spec),
            min_endpoints=3,
            today=date(2026, 11, 24),
        )
        doc = contract.strict_loads(built.payload)
        parsed = contract.validate_report(doc)  # raises ReportRefused on any refusal
        assert parsed.rejected == [], [p.to_json() for p in parsed.rejected]
        assert len(parsed.accepted) == len(doc["patterns"])
        built_reports += 1
    assert built_reports == 200
