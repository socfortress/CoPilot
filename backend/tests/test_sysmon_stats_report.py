"""Building one customer's weekly report (report.py, config_state.py): the exact bytes, the selection, the caps,
``truncated``, the merge after redaction, and sysmon-sync's own validator run before anything is sent.

Run with: cd backend && python -m pytest tests/test_sysmon_stats_report.py
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.services.sysmon_stats import report as rep  # noqa: E402
from app.active_response.services.sysmon_stats.config_state import (  # noqa: E402
    config_value,
)
from app.active_response.services.sysmon_stats.contract_v1 import (  # noqa: E402
    ReportRefused,
)
from app.active_response.services.sysmon_stats.contract_v1 import (  # noqa: E402
    validate_report,
)
from app.active_response.services.sysmon_stats.queries import RawPattern  # noqa: E402
from app.active_response.services.sysmon_stats.redaction import (  # noqa: E402
    build_context,
)

GOLDEN = Path(__file__).parent / "fixtures" / "sysmon_stats" / "expected_report.json"
CUSTOMER = "cust_" + "ab" * 16
TODAY = date(2026, 11, 24)
SYSTEM = "NT AUTHORITY\\\\SYSTEM"
AGENT = "C:\\\\Program Files\\\\Fabrikam\\\\agent.exe"


def ctx():
    return build_context(customer_code="contoso", customer_name="Contoso Ltd", install_dirs=["edrsvc"])


def dns(name, events, endpoints=5, days=127, user=SYSTEM, rule="-"):
    return RawPattern(
        22,
        {"Image": AGENT, "QueryName": name},
        events,
        endpoints,
        days,
        {"QueryStatus": ["0"], "User": [user]},
        [rule] if rule else None,
    )


def golden_patterns():
    return [
        dns("telemetry.fabrikam-example.com", 6100, endpoints=38),
        RawPattern(
            13,
            {"Image": AGENT, "TargetObject": "HKLM\\\\SOFTWARE\\\\Fabrikam\\\\Agent\\\\State"},
            912,
            12,
            31,
            {"User": [SYSTEM]},
            None,
        ),
        RawPattern(
            1,
            {
                "Image": "C:\\\\Program Files\\\\edrsvc\\\\chainsaw\\\\chainsaw.exe",
                "ParentImage": "C:\\\\Windows\\\\System32\\\\svchost.exe",
            },
            400,
            9,
            0b0011111,
            {"OriginalFileName": ["chainsaw.exe"], "User": [SYSTEM], "IntegrityLevel": ["System"]},
            ["-"],
        ),
        RawPattern(
            11,
            {"Image": AGENT, "TargetFilename": "C:\\\\Users\\\\svc_fabrikam\\\\AppData\\\\Local\\\\Fabrikam\\\\cache.tmp"},
            300,
            6,
            127,
            {"User": ["CONTOSO\\\\svc_fabrikam"]},
            ["-"],
        ),
        dns("printer01.local", 5000),
        dns("rare.fabrikam-example.com", 99999, endpoints=2),
    ]


def build(patterns=None, **kw):
    args = dict(
        customer=CUSTOMER,
        week="2026-W47",
        config=56,
        endpoints=40,
        raw_patterns=patterns if patterns is not None else golden_patterns(),
        ctx=ctx(),
        min_endpoints=3,
        today=TODAY,
    )
    args.update(kw)
    return rep.build_report(**args)


def test_the_report_is_the_golden_one_byte_for_byte():
    built = build()
    assert built.payload == GOLDEN.read_bytes().rstrip(b"\n")
    assert built.sha256 == hashlib.sha256(built.payload).hexdigest()
    assert built.sha256 == "c5d05ce48d7f6764992f9646ef3d536c20df8c0a49f819076376c0444d9385dc"
    doc = json.loads(built.payload)
    assert set(doc) == {"format", "customer", "week", "config", "endpoints", "truncated", "patterns"}
    assert [p["event_id"] for p in doc["patterns"]] == [22, 13, 1, 11]
    assert built.stats.dropped_by_reason == {"below-min-endpoints": 1, "dns-private-suffix": 1}
    parsed = validate_report(doc)
    assert parsed.rejected == [] and len(parsed.accepted) == 4
    assert b"svc_fabrikam" not in built.payload and b"CommandLine" not in built.payload
    assert "__INSTALLDIRNAME__" in doc["patterns"][2]["fields"]["Image"]


def test_compact_utf8_and_deterministic():
    built = build([dns("caf\u00e9.fabrikam-example.com", 10)])
    assert built.stats.dropped_by_reason == {"value-rule-non-ascii-dns": 1}
    p = RawPattern(11, {"Image": AGENT, "TargetFilename": "C:\\\\ProgramData\\\\Fabrikam\\\\r\u00e9sum\u00e9.tmp"}, 5, 3, 1, {}, None)
    built = build([p])
    assert "r\u00e9sum\u00e9".encode("utf-8") in built.payload and b"\\u00e9" not in built.payload
    assert build([p]).sha256 == built.sha256


def test_the_threshold_and_the_70_cap():
    many = [dns(f"n{i}.fabrikam-example.com", 1000 - i) for i in range(75)]
    built = build(many)
    doc = built.doc
    assert len(doc["patterns"]) == 70 and doc["truncated"] is True
    assert doc["patterns"][0]["fields"]["QueryName"] == "n0.fabrikam-example.com"
    assert [p["events"] for p in doc["patterns"]] == sorted((p["events"] for p in doc["patterns"]), reverse=True)


@pytest.mark.parametrize(
    "kw,expected",
    [
        ({}, False),
        ({"pairs_left_out": True}, True),
        # A cut tail with fewer than 70 patterns sent could have qualified
        ({"cut_tails": [1]}, True),
    ],
)
def test_truncated_rules(kw, expected):
    assert build([dns("a.fabrikam-example.com", 10)], **kw).doc["truncated"] is expected


def test_a_cut_tail_below_the_smallest_sent_pattern_does_not_truncate():
    many = [dns(f"n{i}.fabrikam-example.com", 1000 + i) for i in range(70)]
    assert build(many, cut_tails=[999]).doc["truncated"] is False
    assert build(many, cut_tails=[1000]).doc["truncated"] is True


def test_payload_size_trimming_sets_truncated(monkeypatch):
    many = [dns(f"n{i}.fabrikam-example.com", 1000 - i) for i in range(20)]
    full = build(many)
    monkeypatch.setattr(rep.settings, "MAX_REPORT_BYTES", len(full.payload) - 50)
    trimmed = build(many)
    assert len(trimmed.payload) <= len(full.payload) - 50 and trimmed.doc["truncated"] is True
    assert len(trimmed.doc["patterns"]) == 19


def test_endpoints_are_clamped_and_days_kept():
    built = build([dns("a.fabrikam-example.com", 10, endpoints=55, days=0b1000001)], endpoints=40)
    (p,) = built.doc["patterns"]
    assert p["endpoints"] == 40 and p["days"] == 65


def test_a_rule_name_and_a_detail_need_every_event():
    built = build(
        [RawPattern(22, {"Image": AGENT, "QueryName": "a.fabrikam-example.com"}, 10, 5, 1, {"QueryStatus": None, "User": [SYSTEM]}, None)],
    )
    (p,) = built.doc["patterns"]
    assert "rule_name" not in p and "QueryStatus" not in p["fields"] and p["fields"]["User"] == "NT AUTHORITY\\SYSTEM"


def test_the_local_validator_removes_a_rejected_pattern():
    bogus = RawPattern(12, {"Image": AGENT, "TargetObject": "HKLM\\\\SOFTWARE\\\\Fabrikam\\\\k", "EventType": "Bogus"}, 50, 5, 1, {}, None)
    built = build([bogus, dns("a.fabrikam-example.com", 10)])
    assert [p["event_id"] for p in built.doc["patterns"]] == [22]
    assert built.stats.dropped_by_reason["local-validator-rejected"] == 1


def test_a_report_the_validator_refuses_is_never_sent(monkeypatch):
    def refuse(doc):
        raise ReportRefused("identity-leak")

    monkeypatch.setattr(rep, "validate_report", refuse)
    with pytest.raises(rep.LocalRefusal) as raised:
        build()
    assert raised.value.reason == "identity-leak"


def test_a_week_the_service_would_refuse_is_never_built():
    with pytest.raises(rep.LocalRefusal):
        build(week="2026-W40")
    with pytest.raises(rep.LocalRefusal):
        build(week="2026-W48")  # not complete yet


def test_an_empty_report_is_valid():
    built = build([dns("printer01.local", 50)])
    assert built.doc["patterns"] == [] and validate_report(built.doc).accepted == []


# ── config ──────────────────────────────────────────────────────────────────

TEMPLATE = (
    b'<Sysmon schemaversion="4.90">\n  <Image condition="begin with">C:\\Program Files\\__INSTALLDIRNAME__\\chainsaw\\</Image>\n</Sysmon>\n'
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crlf(data):
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def test_config_is_the_release_the_stored_config_was_rendered_from():
    rendered = TEMPLATE.replace(b"__INSTALLDIRNAME__", b"edrsvc")
    releases = {56: (sha(TEMPLATE), sha(crlf(TEMPLATE)))}
    assert config_value(rendered, releases, ["edrsvc"]) == 56
    assert config_value(crlf(rendered), releases, ["edrsvc"]) == 56
    older = TEMPLATE.replace(b"4.90", b"4.91")
    assert config_value(rendered, {57: (sha(older), sha(crlf(older))), 56: releases[56]}, ["edrsvc"]) == 56
    assert config_value(rendered + b"<!-- local -->\n", releases, ["edrsvc"]) == "customized"
    assert config_value(rendered, releases, ["another"]) == "customized"
    assert config_value(None, releases, ["edrsvc"]) == "unknown"
    assert config_value(rendered, {}, ["edrsvc"]) == "unknown"
    assert config_value(b"\xff\xfe", releases, ["edrsvc"]) == "unknown"
