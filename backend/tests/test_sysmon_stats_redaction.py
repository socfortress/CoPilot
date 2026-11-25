r"""The redaction of the Sysmon noise statistics (app/active_response/services/sysmon_stats/redaction.py, dns_policy.py).

Golden cases in tests/fixtures/sysmon_stats/redaction_cases.json, all synthetic: each raw value (as the indexer holds it,
JSON-escaped once more by Wazuh unless the case says otherwise) must come out as the expected value, or drop its pattern
for the expected reason. Every value that comes out passes sysmon-sync's own identity and value checks (the vendored
contract). Then the pattern-level steps: key fields, detail sameness on redacted values, the rule name, the 5-field cap,
collisions merged after redaction.

Run with: cd backend && python -m pytest tests/test_sysmon_stats_redaction.py
"""
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.services.sysmon_stats import redaction as r  # noqa: E402
from app.active_response.services.sysmon_stats.contract_v1 import (  # noqa: E402
    service_leak,
)
from app.active_response.services.sysmon_stats.contract_v1_rules import (  # noqa: E402
    REGISTRY_SERVICE_HIVES,
)
from app.active_response.services.sysmon_stats.contract_v1_rules import (  # noqa: E402
    identity_leak,
)
from app.active_response.services.sysmon_stats.contract_v1_rules import (  # noqa: E402
    value_reasons,
)
from app.active_response.services.sysmon_stats.dns_policy import Drop  # noqa: E402
from app.active_response.services.sysmon_stats.queries import RawPattern  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sysmon_stats" / "redaction_cases.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
CASES = DATA["cases"]


def ctx_for(spec):
    return r.build_context(**spec)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_redaction(case):
    ctx = ctx_for(case.get("ctx") or DATA["default_ctx"])
    got = r.redact_value(case["field"], case["raw"], ctx)
    if "drop" in case["expect"]:
        assert isinstance(got, Drop), f"expected a drop, got {got!r}"
        assert got.reason == case["expect"]["drop"]
    else:
        assert got == case["expect"]["value"]
        # What comes out passes sysmon-sync's own checks
        assert value_reasons(case["field"], got) == []
        assert identity_leak(case["field"], got, REGISTRY_SERVICE_HIVES) is None and service_leak(got) is None


def test_the_cases_cover_every_drop_reason_the_spec_names():
    reasons = {c["expect"].get("drop") for c in CASES} - {None}
    for wanted in (
        "dns-ip-literal",
        "dns-single-label",
        "dns-service-record",
        "dns-reverse-lookup",
        "dns-private-suffix",
        "dns-own-domain",
        "dns-identity-token",
        "dns-ip-label",
        "identity-unredacted",
        "value-too-long",
        "value-empty",
        "value-rule-wildcard",
        "value-rule-env-var",
        "value-rule-not-nfc",
        "value-rule-bad-character",
        "value-rule-look-alike",
        "value-rule-non-ascii-dns",
        "value-rule-unknown-placeholder",
        "value-rule-unknown-token",
        "value-rule-doubled-backslash",
    ):
        assert wanted in reasons, wanted


def test_unescaping_is_the_installer_repos_conservative_rule():
    assert r.unescape_value("C:\\\\Windows\\\\x") == "C:\\Windows\\x"
    assert r.unescape_value("C:\\Windows\\x") == "C:\\Windows\\x"  # \W is no escape
    assert r.unescape_value("\\\\nas\\files") == "\\\\nas\\files"  # \f makes it ambiguous
    assert r.unescape_value('say \\"hi\\" C:\\\\x') == 'say "hi" C:\\x'
    assert r.unescape_value("\\u0041\\\\x") == "\\u0041\\\\x"  # a \u escape: left alone


def test_names_are_never_matched_inside_placeholders():
    ctx = r.RedactionContext()
    ctx.names.update({"user", "sid", "host", "redacted", "installdirname"})
    value = "C:\\Users\\<user>\\x <SID> <host> <redacted> C:\\Program Files\\__INSTALLDIRNAME__\\y"
    assert r.redact_names(value, ctx) == value


def test_names_are_whole_words_and_case_insensitive():
    ctx = r.build_context(customer_code="fab", customer_name="Fabrikam Holdings")
    assert r.redact_names("C:\\FAB\\fabrikam\\Fabrikamx\\xfab", ctx) == "C:\\<redacted>\\<redacted>\\Fabrikamx\\xfab"
    assert "holdings" not in ctx.names  # a stopword
    assert "fabrikam holdings" in ctx.names


def test_learned_accounts_and_domains():
    ctx = r.build_context(
        customer_code="c1",
        customer_name=None,
        accounts=[
            "NORTHWIND\\\\a.smith",
            "b.jones@northwind-example.com",
            "SRV-APP01$",
            "NT AUTHORITY\\\\SYSTEM",
            "BUILTIN\\\\Administrators",
            "Administrator",
        ],
    )
    assert {"northwind", "a.smith", "b.jones", "srv-app01"} <= ctx.names
    assert "northwind-example.com" in ctx.own_domains and "northwind-example" in ctx.names
    assert "administrator" not in ctx.names and "system" not in ctx.names and "builtin" not in ctx.names


def test_the_rule_name_is_redacted_or_left_out_never_the_pattern():
    ctx = ctx_for(DATA["default_ctx"])
    assert r.redact_rule_name("technique_id=T1036,technique_name=Masquerading", ctx) == "technique_id=T1036,technique_name=Masquerading"
    assert r.redact_rule_name("Contoso allow-list", ctx) == "<redacted> allow-list"
    assert r.redact_rule_name("bad\u202ename", ctx) is None
    assert r.redact_rule_name("x" * 300, ctx) is None
    assert r.redact_rule_name("", ctx) is None

    raw = RawPattern(
        eid=11,
        key={"Image": "C:\\\\Program Files\\\\Fabrikam\\\\agent.exe", "TargetFilename": "C:\\\\ProgramData\\\\Fabrikam\\\\x.tmp"},
        events=10,
        endpoints=4,
        days=1,
        details={"User": ["NT AUTHORITY\\\\SYSTEM"]},
        rule_names=["bad\u202ename"],
    )
    p = r.redact_pattern(raw, ctx)
    assert not isinstance(p, Drop) and p.rule_name is None
    assert p.fields == {
        "Image": "C:\\Program Files\\Fabrikam\\agent.exe",
        "TargetFilename": "C:\\ProgramData\\Fabrikam\\x.tmp",
        "User": "NT AUTHORITY\\SYSTEM",
    }


def _raw(eid=11, key=None, details=None, rule_names=None, events=10, endpoints=4, days=1):
    return RawPattern(
        eid=eid,
        key=key or {"Image": "C:\\\\Fab\\\\a.exe", "TargetFilename": "C:\\\\ProgramData\\\\Fab\\\\x.tmp"},
        events=events,
        endpoints=endpoints,
        days=days,
        details=details or {},
        rule_names=rule_names,
    )


def test_a_detail_is_sent_only_when_every_event_shares_it_once_redacted():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    # Two different accounts both become <redacted>: shared once redacted
    p = r.redact_pattern(_raw(details={"User": ["FAB\\\\alice", "FAB\\\\bob"]}), ctx)
    assert p.fields["User"] == "<redacted>"
    # A service account and a person: not the same
    p = r.redact_pattern(_raw(details={"User": ["NT AUTHORITY\\\\SYSTEM", "FAB\\\\bob"]}), ctx)
    assert "User" not in p.fields
    # Not covering every event: never sent
    p = r.redact_pattern(_raw(details={"User": None}), ctx)
    assert "User" not in p.fields


def test_a_key_value_that_cannot_be_redacted_drops_the_pattern():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    assert r.redact_pattern(_raw(key={"Image": "C:\\\\Fab\\\\a.exe", "TargetFilename": "%TEMP%\\\\x"}), ctx) == Drop("value-rule-env-var")
    assert r.redact_pattern(_raw(key={"Image": "C:\\\\Fab\\\\a.exe"}), ctx) == Drop("key-field-missing")


def test_a_network_connect_without_a_host_name_is_dropped():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    raw = _raw(eid=3, key={"Image": "C:\\\\Fab\\\\a.exe", "DestinationHostname": "-", "DestinationPort": "443"})
    assert r.redact_pattern(raw, ctx) == Drop("ip-destination")
    raw = _raw(eid=3, key={"Image": "C:\\\\Fab\\\\a.exe", "DestinationHostname": "api.fabrikam-example.com", "DestinationPort": "443"})
    p = r.redact_pattern(raw, ctx)
    assert list(p.fields) == ["Image", "DestinationPort", "DestinationHostname"]
    assert p.key_fields == {"Image": "C:\\Fab\\a.exe", "DestinationPort": "443", "DestinationHostname": "api.fabrikam-example.com"}


def test_the_fields_are_capped_at_5_in_the_plans_order():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    raw = RawPattern(
        eid=7,
        key={"Image": "C:\\\\Fab\\\\a.exe", "ImageLoaded": "C:\\\\Fab\\\\b.dll", "Signature": "Fabrikam, Inc."},
        events=5,
        endpoints=3,
        days=1,
        details={"SignatureStatus": ["Valid"], "Signed": ["true"], "OriginalFileName": ["b.dll"], "User": ["NT AUTHORITY\\\\SYSTEM"]},
    )
    p = r.redact_pattern(raw, ctx)
    assert list(p.fields) == ["Image", "ImageLoaded", "Signature", "SignatureStatus", "Signed"]


def test_registry_event_types():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    p = r.redact_pattern(
        RawPattern(
            eid=12,
            key={"Image": "C:\\\\Fab\\\\a.exe", "TargetObject": "HKLM\\\\SOFTWARE\\\\Fab\\\\k", "EventType": "CreateKey"},
            events=5,
            endpoints=3,
            days=1,
        ),
        ctx,
    )
    assert p.fields["EventType"] == "CreateKey" and p.key_fields["EventType"] == "CreateKey"
    p13 = r.redact_pattern(
        RawPattern(
            eid=13,
            key={"Image": "C:\\\\Fab\\\\a.exe", "TargetObject": "HKLM\\\\SOFTWARE\\\\Fab\\\\k"},
            events=5,
            endpoints=3,
            days=1,
        ),
        ctx,
    )
    assert "EventType" not in p13.fields and p13.key_fields["EventType"] == "SetValue"


def test_collisions_after_redaction_are_merged_without_inflating_endpoints():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    a = r.redact_pattern(
        _raw(
            key={"Image": "C:\\\\Fab\\\\a.exe", "TargetFilename": "C:\\\\Users\\\\alice\\\\AppData\\\\x.tmp"},
            events=10,
            endpoints=4,
            days=1,
            details={"User": ["NT AUTHORITY\\\\SYSTEM"]},
            rule_names=["-"],
        ),
        ctx,
    )
    b = r.redact_pattern(
        _raw(
            key={"Image": "C:\\\\Fab\\\\a.exe", "TargetFilename": "C:\\\\Users\\\\bob\\\\AppData\\\\x.tmp"},
            events=7,
            endpoints=6,
            days=2,
            details={"User": ["FAB\\\\bob"]},
            rule_names=["-"],
        ),
        ctx,
    )
    merged, count = r.merge_collisions([a, b])
    assert count == 1 and len(merged) == 1
    (m,) = merged
    assert (m.events, m.endpoints, m.days) == (17, 6, 3)
    assert "User" not in m.fields and m.rule_name == "-"
    assert m.fields["TargetFilename"] == "C:\\Users\\<user>\\AppData\\x.tmp"


def test_a_value_is_never_case_folded_or_normalised():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    assert r.redact_value("Image", "C:\\\\PROGRAM FILES\\\\Fabrikam\\\\Agent.EXE", ctx) == "C:\\PROGRAM FILES\\Fabrikam\\Agent.EXE"
