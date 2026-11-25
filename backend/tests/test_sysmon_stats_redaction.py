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
import re
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.services.sysmon_stats import contract_v1  # noqa: E402
from app.active_response.services.sysmon_stats import contract_v1_rules as rules  # noqa: E402
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
    # OriginalFileName before SignatureStatus (review: SOCFortress's ImageLoad includes match on it); Signed never
    assert list(p.fields) == ["Image", "ImageLoaded", "Signature", "OriginalFileName", "SignatureStatus"]
    assert p.fields["OriginalFileName"] == "b.dll"


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


# ── a user SID glued to a word (the installer repo's and sysmon-sync's SID_PATTERN) ───────────────────────────────────
GLUED_SIDS = [
    "C:\\Windows\\System32\\Tasks\\GoogleUpdateTaskUserS-1-5-21-1111111111-2222222222-3333333333-1001Core",
    "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Schedule\\TaskCache\\Tree\\MicrosoftEdgeUpdateTaskUserS-1-5-21-1-2-3-1001UA",
    "C:\\ProgramData\\Fabrikam\\x_S-1-5-21-1111111111-2222222222-3333333333-1001\\y",
    "C:\\ProgramData\\Fabrikam\\1S-1-12-1-1111111111-2222222222-3333333333-4444444444\\y",
    "xHKU\\S-1-5-21-1-2-3-1001\\Software",
]


def test_one_sid_rule_with_the_contract_and_no_leading_word_boundary():
    """The redactor's SID rule is the contract's SID_PATTERN (no leading \\b), and no identity regex of the redactor or
    the vendored contract looks for a SID only after a word boundary."""
    assert r.SID_RE.pattern == "(?i)" + rules.SID_PATTERN
    assert rules.SID_RE.pattern == "(?i)" + rules.SID_PATTERN + "(?:_Classes)?"
    for module in (r, rules, contract_v1):
        for name, value in vars(module).items():
            if isinstance(value, re.Pattern):
                assert not re.search(r"\\b(?:\(\?[a-z]*[:)])?S-1", value.pattern, re.I), f"{module.__name__}.{name}"


@pytest.mark.parametrize("value", GLUED_SIDS)
def test_a_user_sid_glued_to_a_word_is_refused_unredacted_and_redacted(value):
    ctx = r.build_context(customer_code="c1", customer_name=None)
    assert identity_leak("TargetObject", value, REGISTRY_SERVICE_HIVES) == "a user's SID"
    got = r.redact_value("TargetObject", value.replace("\\", "\\\\"), ctx)
    assert isinstance(got, str) and "<SID>" in got and "s-1-5-21" not in got.lower() and "s-1-12-1" not in got.lower()
    assert identity_leak("TargetObject", got, REGISTRY_SERVICE_HIVES) is None


def test_service_sids_are_not_user_sids():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    for sid in ("S-1-5-18", "S-1-5-19", "S-1-5-20", "S-1-5-32-544", "S-1-15-2-1"):
        value = f"C:\\ProgramData\\Fabrikam\\TaskUser{sid}"
        assert r.redact_value("TargetFilename", value, ctx) == value


# ── what a share may hold ─────────────────────────────────────────────────────────────────────────────────────────────
PER_USER_SHARES = [
    "home$",
    "Homes",
    "HomeDirs",
    "UserHomes",
    "Profiles$",
    "TSProfiles",
    "Users",
    "users$",
    "Redirect$",
    "RedirectedFolders",
    "Folders$",
    "UserData",
]
OTHER_SHARES = ["deploy$", "Software", "Apps", "share", "files", "scans$"]


@pytest.mark.parametrize("share", PER_USER_SHARES + OTHER_SHARES)
def test_the_first_folder_below_a_share_is_redacted_also_as_the_last_segment(share):
    ctx = r.build_context(customer_code="c1", customer_name=None)
    for below in ("jsmith", "jsmith.V6", "j.smith", "jsmith.txt", "Board minutes.docx"):
        assert r.redact_value("TargetFilename", f"\\\\fs01\\{share}\\{below}", ctx) == f"\\\\<host>\\{share}\\<redacted>"
    # A folder, also one named like a program, is never kept; what follows it is cut down as in a profile (D9)
    assert r.redact_value("Image", f"\\\\fs01\\{share}\\tools.exe\\x.exe", ctx) == f"\\\\<host>\\{share}\\<redacted>\\<redacted>"
    assert (
        r.redact_value("TargetFilename", f"\\\\fs01\\{share}\\jsmith\\AppData\\x.dat", ctx)
        == f"\\\\<host>\\{share}\\<redacted>\\AppData\\x.dat"
    )


@pytest.mark.parametrize("program", ["agent.msi", "Setup 2.1.exe", "logon.ps1", "map.cmd", "drivers.cab", "Update.msixbundle"])
def test_a_program_directly_below_a_share_is_kept_unless_the_share_holds_user_folders(program):
    ctx = r.build_context(customer_code="c1", customer_name=None)
    for share in OTHER_SHARES:
        assert r.redact_value("Image", f"\\\\fs01\\{share}\\{program}", ctx) == f"\\\\<host>\\{share}\\{program}"
    for share in PER_USER_SHARES:
        assert r.redact_value("Image", f"\\\\fs01\\{share}\\{program}", ctx) == f"\\\\<host>\\{share}\\<redacted>"


def test_a_volume_root_keeps_its_folders_and_redacts_its_profiles():
    ctx = r.build_context(customer_code="c1", customer_name=None)
    assert r.redact_value("Image", "\\\\fs01\\C$\\Windows\\System32\\x.exe", ctx) == "\\\\<host>\\C$\\Windows\\System32\\x.exe"
    assert r.redact_value("Image", "\\\\tsclient\\C\\Tools\\x.exe", ctx) == "\\\\<host>\\C\\Tools\\x.exe"
    for root in ("Users", "Home", "Profiles", "TSProfiles", "UserData", "RedirectedFolders"):
        got = r.redact_value("TargetFilename", f"\\\\fs01\\D$\\{root}\\jsmith\\x.dat", ctx)
        assert got == f"\\\\<host>\\D$\\{root}\\<user>\\<redacted>"
    # A one-letter share is a redirected drive only on tsclient: on a file server it is an ordinary share
    assert r.redact_value("Image", "\\\\fs01\\C\\Tools\\x.exe", ctx) == "\\\\<host>\\C\\<redacted>\\<redacted>"


# ── the customer's own domains, learned from every value of its report (review findings) ─────────────────────────
SVCHOST = "C:\\\\Windows\\\\System32\\\\svchost.exe"
AD = "aw-corp-example.com"


def _p(eid, key, endpoints=8):
    return RawPattern(eid=eid, key=key, events=500, endpoints=endpoints, days=127, details={}, rule_names=None, accounts=[])


def _doubled(value):
    return value.replace("\\", "\\\\")


def _report(ctx, patterns):
    from app.active_response.services.sysmon_stats.report import build_report

    return build_report(
        customer="cust_" + "0" * 32,
        week="2026-W47",
        config="unknown",
        endpoints=20,
        raw_patterns=patterns,
        ctx=ctx,
        min_endpoints=3,
    )


def _acme(**kw):
    spec = {
        "customer_code": "acme",
        "customer_name": "Acme Widgets",
        "hostnames": ["WS-0001", "WS-0002", "DC01"],
        "accounts": ["AWCORP\\\\jdoe"],
    }
    spec.update(kw)
    return r.build_context(**spec)


# Names under the AD domain, which shares no word with the customer's code or name
UNDER_THE_DOMAIN = [
    _p(22, {"Image": SVCHOST, "QueryName": AD}),
    _p(3, {"Image": SVCHOST, "DestinationHostname": f"fs01.{AD}", "DestinationPort": "445"}),
    _p(17, {"Image": SVCHOST, "PipeName": _doubled(f"\\{AD}\\sync")}),
]
VENDOR = _p(22, {"Image": SVCHOST, "QueryName": "telemetry.fabrikam-example.com"})


@pytest.mark.parametrize(
    "evidence",
    [
        pytest.param([_p(22, {"Image": SVCHOST, "QueryName": f"WS-0002.{AD}"})], id="an-agents-fqdn-looked-up"),
        pytest.param([_p(22, {"Image": SVCHOST, "QueryName": f"_ldap._tcp.dc._msdcs.{AD}"})], id="an-ad-locator-record"),
        pytest.param([_p(22, {"Image": SVCHOST, "QueryName": f"_kerberos._tcp.Default-First-Site-Name._sites.{AD}"})], id="a-site-locator"),
        pytest.param([_p(22, {"Image": SVCHOST, "QueryName": f"wpad.{AD}"})], id="wpad"),
        pytest.param(
            [_p(1, {"Image": _doubled(f"\\\\{AD}\\SYSVOL\\{AD}\\scripts\\deploy.exe"), "ParentImage": SVCHOST})],
            id="a-sysvol-share",
        ),
        pytest.param(
            [
                _p(
                    11,
                    {
                        "Image": SVCHOST,
                        "TargetFilename": _doubled(f"C:\\Windows\\System32\\GroupPolicy\\DataStore\\0\\sysvol\\{AD}\\Policies\\gpt.ini"),
                    },
                ),
            ],
            id="the-group-policy-cache",
        ),
        pytest.param([_p(1, {"Image": _doubled(f"\\\\{AD}\\NETLOGON\\logon.exe"), "ParentImage": SVCHOST})], id="a-netlogon-share"),
    ],
)
def test_the_ad_domain_is_learned_from_any_value_whatever_the_patterns_order(evidence):
    """Review: with only short agent names known (Wazuh's usual), the AD domain went out verbatim in DNS names, SYSVOL
    paths and pipes. One value that reveals it now keeps it out of every other, before or after it."""
    for patterns in (UNDER_THE_DOMAIN + evidence + [VENDOR], evidence + [VENDOR] + UNDER_THE_DOMAIN):
        built = _report(_acme(), patterns)
        text = json.dumps(built.doc)
        assert AD not in text and "aw-corp" not in text, text
        assert "telemetry.fabrikam-example.com" in text


def test_the_ad_domain_from_the_computers_names():
    """The Windows event's Computer (WS-0001.aw-corp-example.com), read in stage 1, is a host name like an agent's."""
    built = _report(_acme(hostnames=["WS-0001", f"WS-0001.{AD}"]), UNDER_THE_DOMAIN + [VENDOR])
    assert built.stats.dropped_by_reason == {"dns-own-domain": 2}
    assert [p["fields"].get("QueryName") for p in built.doc["patterns"] if p["event_id"] == 22] == ["telemetry.fabrikam-example.com"]
    (pipe,) = [p["fields"]["PipeName"] for p in built.doc["patterns"] if p["event_id"] == 17]
    assert pipe == "\\<redacted>\\sync"


def test_a_single_label_ad_domain_from_a_computers_name_is_a_name():
    ctx = r.build_context(customer_code="acme", customer_name=None, hostnames=["WS-0001.awcorp"])
    assert "awcorp" in ctx.names and "ws-0001" in ctx.hosts
    assert r.redact_value("QueryName", "fs01.awcorp", ctx) == Drop("dns-identity-token")


def test_a_providers_domain_is_never_learned_as_the_customers():
    ctx = _acme()
    built = _report(
        ctx,
        [_p(22, {"Image": SVCHOST, "QueryName": "autodiscover.outlook.com"}), _p(22, {"Image": SVCHOST, "QueryName": "smtp.outlook.com"})],
    )
    assert "outlook.com" not in ctx.own_domains
    assert sorted(p["fields"]["QueryName"] for p in built.doc["patterns"]) == ["autodiscover.outlook.com", "smtp.outlook.com"]


def test_the_reviewers_privacy_probe_sends_nothing_of_the_customer():
    """The review's probe, transcribed (its domain as aw-corp-example.com): the customer's AD domain, a printer's address,
    its public domain written as one word, a print server and share, an admin share's profile. sysmon-sync's validator
    accepted all of them before; now none goes out unredacted."""
    patterns = [
        _p(22, {"Image": SVCHOST, "QueryName": f"WS-0002.{AD}"}),
        _p(22, {"Image": SVCHOST, "QueryName": AD}),
        _p(3, {"Image": SVCHOST, "DestinationHostname": f"fs01.{AD}", "DestinationPort": "445"}),
        _p(
            1,
            {
                "Image": _doubled(f"\\\\{AD}\\SYSVOL\\{AD}\\scripts\\deploy.exe"),
                "ParentImage": _doubled("C:\\Windows\\System32\\gpscript.exe"),
            },
        ),
        _p(
            11,
            {
                "Image": SVCHOST,
                "TargetFilename": _doubled(
                    f"C:\\Windows\\System32\\GroupPolicy\\DataStore\\0\\sysvol\\{AD}\\Policies\\{{31B2F340-016D-11D2-945F-00C04FB984F9}}\\Machine\\Registry.pol",
                ),
            },
        ),
        _p(
            13,
            {
                "Image": _doubled("C:\\Windows\\System32\\spoolsv.exe"),
                "TargetObject": _doubled(
                    "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Print\\Monitors\\Standard TCP/IP Port\\Ports\\10.20.30.40\\HostName",
                ),
            },
        ),
        _p(
            22,
            {
                "Image": _doubled("C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE"),
                "QueryName": "autodiscover.acmewidgets.com",
            },
        ),
        _p(11, {"Image": SVCHOST, "TargetFilename": _doubled("C:\\ProgramData\\AcmeWidgets\\agent\\cache.db")}),
        _p(
            13,
            {
                "Image": _doubled("C:\\Windows\\System32\\spoolsv.exe"),
                "TargetObject": _doubled(
                    "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Print\\Connections\\,,printsrv01,HP Floor2 Finance",
                ),
            },
        ),
        _p(11, {"Image": SVCHOST, "TargetFilename": _doubled("\\\\WS-0009\\C$\\Users\\jsmith\\AppData\\Local\\Temp\\x.tmp")}),
    ]
    built = _report(_acme(), patterns)
    text = json.dumps(built.doc).lower()
    for leaked in ("aw-corp", "10.20.30.40", "acmewidgets", "printsrv01", "floor2", "jsmith", "ws-0009", "ws-0002"):
        assert leaked not in text, leaked
    for p in built.doc["patterns"]:
        for name, value in p["fields"].items():
            assert identity_leak(name, value, REGISTRY_SERVICE_HIVES) is None and value_reasons(name, value) == []
