"""In-context exclusion creation from Incident Management (#934).

Velociraptor Sigma exclusion rules used to be creatable only from Sources, forcing an analyst who
spotted a false positive to leave the alert and retype channel, title and field values by hand.
The exclusion matcher is exact on channel / title and looks field names up in a flattened
``EventData`` map, so a retyped rule that is off by one character silently never matches.

These tests pin the pieces that make the in-context path trustworthy:

* the original Sigma payload is recovered from the comments the ingest leaves on the alert,
  for both the Wazuh-matched and the fallback writer;
* the draft offers exactly the field names the matcher will look up, with stable fields
  suggested and volatile ones (ids, GUIDs, timestamps) flagged;
* the dry-run reuses the ingest-time matcher, so "matches" means the next identical alert
  is suppressed, and a non-match names the failing criterion;
* customer-scoped rules compare against the resolved tenant, not a hard-coded ``"unknown"``.

No DB, no network -- the session is faked.

Run with: cd backend && python -m pytest tests/test_velo_sigma_exclusion_draft.py
"""

import asyncio
import json
import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.incidents.models import VeloSigmaExclusion  # noqa: E402
from app.incidents.schema.db_operations import AlertOut  # noqa: E402
from app.incidents.schema.db_operations import AssetBase  # noqa: E402
from app.incidents.schema.db_operations import CommentBase  # noqa: E402
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlert  # noqa: E402
from app.incidents.schema.velo_sigma import (  # noqa: E402
    VeloSigmaExclusionDryRunRequest,
)
from app.incidents.services import velo_sigma  # noqa: E402
from app.incidents.services.velo_sigma import VeloSigmaExclusionService  # noqa: E402

SYSMON_EVENT = {
    "System": {
        "Provider": {"Name": "Microsoft-Windows-Sysmon", "Guid": "5770385F-C22A-43E0-BF4C-06F5698FFBD9"},
        "EventID": {"Value": 10},
        "Version": 3,
        "Level": 4,
        "Task": 10,
        "Opcode": 0,
        "Keywords": 9223372036854775808,
        "TimeCreated": {"SystemTime": 1744233485.0778975},
        "EventRecordID": 564617,
        "Correlation": {},
        "Execution": {"ProcessID": 2320, "ThreadID": 3540},
        "Channel": "Microsoft-Windows-Sysmon/Operational",
        "Computer": "WIN-HFOU106TD7K",
        "Security": {"UserID": "S-1-5-18"},
    },
    "EventData": {
        "RuleName": "technique_id=T1003,technique_name=Credential Dumping",
        "UtcTime": "2025-04-09 21:18:05.064",
        "SourceProcessGUID": "691FF406-E40B-67F6-2901-000000003A00",
        "SourceProcessId": 4964,
        "SourceThreadId": 4448,
        "SourceImage": "C:\\Program Files\\Backup Agent\\agent.exe",
        "TargetProcessGUID": "691FF406-DDC8-67F6-0C00-000000003A00",
        "TargetProcessId": 668,
        "TargetImage": "C:\\Windows\\system32\\lsass.exe",
        "GrantedAccess": 2097151,
        "CallTrace": "C:\\Windows\\SYSTEM32\\ntdll.dll+9fc24",
        "SourceUser": "WIN-HFOU106TD7K\\svc_backup",
        "TargetUser": "NT AUTHORITY\\SYSTEM",
    },
    "Message": "Process accessed",
}

TITLE = "Proc Access (Sysmon Alert)"
CHANNEL = "Microsoft-Windows-Sysmon/Operational"


def _payload_comment(event=SYSMON_EVENT) -> str:
    # Byte-for-byte what `_create_copilot_alert` writes.
    return f"Full Event Payload:\n```\n{json.dumps(event, indent=2)}\n```"


def _alert(comments, *, alert_id=42, customer_code="acme", assets=None) -> AlertOut:
    return AlertOut(
        id=alert_id,
        alert_creation_time="2025-04-09T21:18:05",
        alert_name="Sysmon rule fired",
        alert_description="desc",
        status="OPEN",
        customer_code=customer_code,
        source="wazuh",
        comments=[
            CommentBase(id=i + 1, alert_id=alert_id, comment=c, user_name="admin", created_at="2025-04-09T21:18:06")
            for i, c in enumerate(comments)
        ],
        assets=assets or [],
    )


def _wazuh_matched_alert(**kw) -> AlertOut:
    return _alert([f"Velociraptor Sigma: {TITLE} | {CHANNEL}", _payload_comment()], **kw)


class FakeSession:
    """The draft builder and dry-run never touch the DB; any call is a regression."""

    async def execute(self, *_a, **_k):
        raise AssertionError("dry-run must not hit the database")


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Payload recovery from comments
# ---------------------------------------------------------------------------


def test_parse_comments_from_wazuh_matched_writer():
    title, channel, event = velo_sigma.parse_sigma_comments([f"Velociraptor Sigma: {TITLE} | {CHANNEL}", _payload_comment()])
    assert (title, channel) == (TITLE, CHANNEL)
    assert event == SYSMON_EVENT


def test_parse_comments_from_fallback_writer():
    meta = (
        "Velociraptor Sigma Alert (No Wazuh match found)\n"
        f"Title: {TITLE}\n"
        f"Channel: {CHANNEL}\n"
        "Level: high\n"
        "Computer: WIN-HFOU106TD7K\n"
        "Event Type: SysmonEvent\n"
    )
    title, channel, event = velo_sigma.parse_sigma_comments([meta, _payload_comment()])
    assert (title, channel) == (TITLE, CHANNEL)
    assert event == SYSMON_EVENT


def test_title_containing_pipe_splits_from_the_right():
    title, channel, _ = velo_sigma.parse_sigma_comments([f"Velociraptor Sigma: A | B (Sysmon) | {CHANNEL}"])
    assert title == "A | B (Sysmon)"
    assert channel == CHANNEL


def test_unrelated_comments_and_bad_json_are_ignored():
    title, channel, event = velo_sigma.parse_sigma_comments(
        ["Looks benign to me", "Full Event Payload:\n```\n{not json\n```", ""],
    )
    assert (title, channel, event) == (None, None, None)


def test_non_sigma_alert_yields_no_sigma_alert_and_no_draft():
    alert = _alert(["Escalated to L2"])
    assert velo_sigma.sigma_alert_from_copilot_alert(alert) is None
    assert velo_sigma.build_exclusion_draft(alert) is None


def test_meta_only_alert_still_drafts_without_field_candidates():
    """Seen on a real deployment: the meta comment survived, the payload comment did not."""
    alert = _alert([f"Velociraptor Sigma: {TITLE} | {CHANNEL}"])
    draft = velo_sigma.build_exclusion_draft(alert)
    assert draft is not None
    assert (draft.title, draft.channel, draft.customer_code) == (TITLE, CHANNEL, "acme")
    assert draft.payload_available is False
    assert draft.fields == []

    # Title/channel/customer can still be dry-run; field matches are reported as unverifiable.
    service = VeloSigmaExclusionService(FakeSession())
    ok = run(service.dry_run(alert, VeloSigmaExclusionDryRunRequest(title=TITLE, channel=CHANNEL, customer_code="acme")))
    assert ok.matches is True
    with_fields = run(service.dry_run(alert, VeloSigmaExclusionDryRunRequest(title=TITLE, field_matches={"SourceImage": "x"})))
    assert with_fields.matches is False
    assert with_fields.reasons == ["Alert stores no event payload, so field matches cannot be verified against it"]


def test_channel_falls_back_to_system_channel_and_client_id_comes_from_asset():
    asset = AssetBase(
        id=1,
        alert_linked=42,
        asset_name="WIN-HFOU106TD7K",
        alert_context_id=1,
        agent_id="001",
        velociraptor_id="C.475df76785008b04",
        customer_code="acme",
        index_id="x",
        index_name="wazuh-alerts",
    )
    alert = _alert([_payload_comment()], assets=[asset])
    sigma = velo_sigma.sigma_alert_from_copilot_alert(alert)
    assert sigma.channel == CHANNEL
    assert sigma.clientID == "C.475df76785008b04"
    assert sigma.computer == "WIN-HFOU106TD7K"
    assert sigma.title == ""


# ---------------------------------------------------------------------------
# Draft: offers the matcher's field names, suggests stable ones, flags volatile ones
# ---------------------------------------------------------------------------


def test_draft_prefills_from_alert():
    draft = velo_sigma.build_exclusion_draft(_wazuh_matched_alert())
    assert draft.alert_id == 42
    assert draft.payload_available is True
    assert draft.customer_code == "acme"
    assert draft.channel == CHANNEL
    assert draft.title == TITLE
    assert draft.computer == "WIN-HFOU106TD7K"
    assert draft.name == f"Exclude: {TITLE}"
    assert "alert #42" in draft.description


def test_draft_fields_are_exactly_what_the_matcher_looks_up():
    sigma = velo_sigma.sigma_alert_from_copilot_alert(_wazuh_matched_alert())
    matcher_fields = velo_sigma.extract_event_fields(sigma)
    draft = velo_sigma.build_exclusion_draft(_wazuh_matched_alert())
    offered = {f.name: f.value for f in draft.fields}
    assert offered == {k: v for k, v in matcher_fields.items() if v not in ("", "None")}
    assert "model_config" not in offered


def test_draft_suggests_stable_fields_first_and_flags_volatile_ones():
    draft = velo_sigma.build_exclusion_draft(_wazuh_matched_alert())
    by_name = {f.name: f for f in draft.fields}

    suggested = [f.name for f in draft.fields if f.suggested]
    assert suggested == ["SourceImage", "TargetImage", "SourceUser"]
    assert [f.name for f in draft.fields][: len(suggested)] == suggested

    for volatile in ("UtcTime", "SourceProcessGUID", "SourceProcessId", "SourceThreadId"):
        assert by_name[volatile].volatile, volatile
        assert not by_name[volatile].suggested, volatile
    assert not by_name["SourceImage"].volatile


# ---------------------------------------------------------------------------
# Dry-run: same matcher as ingest, names the failing criterion, never touches the DB
# ---------------------------------------------------------------------------


def _dry_run(rule: dict, alert=None):
    service = VeloSigmaExclusionService(FakeSession())
    return run(service.dry_run(alert or _wazuh_matched_alert(), VeloSigmaExclusionDryRunRequest(**rule)))


def test_dry_run_matches_a_rule_built_from_the_draft():
    draft = velo_sigma.build_exclusion_draft(_wazuh_matched_alert())
    rule = {
        "channel": draft.channel,
        "title": draft.title,
        "customer_code": draft.customer_code,
        "field_matches": {f.name: f.value for f in draft.fields if f.suggested},
    }
    result = _dry_run(rule)
    assert result.matches is True
    assert result.reasons == []


def test_dry_run_names_each_failing_criterion():
    result = _dry_run(
        {
            "channel": "Security",
            "title": TITLE + " (typo)",
            "customer_code": "other",
            "field_matches": {"SourceImage": "C:\\Other\\thing.exe", "NoSuchField": "x"},
        },
    )
    assert result.matches is False
    joined = "\n".join(result.reasons)
    assert "Customer mismatch" in joined
    assert "Channel mismatch" in joined
    assert "Title mismatch" in joined
    assert "'SourceImage' does not match" in joined
    assert "'NoSuchField' is not present" in joined


def test_dry_run_honours_regex_and_case_insensitive_paths():
    assert _dry_run({"field_matches": {"SourceImage": "regex:C:\\Program Files\\Backup Agent\\.*"}}).matches is True
    assert _dry_run({"field_matches": {"SourceImage": "c:\\program files\\backup agent\\agent.exe"}}).matches is True


def test_dry_run_on_non_sigma_alert_explains_instead_of_failing():
    result = _dry_run({"title": TITLE}, alert=_alert(["no payload here"]))
    assert result.matches is False
    assert result.reasons == ["Alert has no Velociraptor Sigma event payload"]


# ---------------------------------------------------------------------------
# Customer-scoped rules compare against the resolved tenant
# ---------------------------------------------------------------------------


def test_customer_scoped_rule_matches_resolved_tenant_and_fails_closed_when_unknown():
    service = VeloSigmaExclusionService(FakeSession())
    sigma = velo_sigma.sigma_alert_from_copilot_alert(_wazuh_matched_alert())
    event_data = velo_sigma.extract_event_fields(sigma)
    scoped = VeloSigmaExclusion(name="r", created_by="t", title=TITLE, customer_code="acme")

    assert run(service._matches_exclusion(sigma, event_data, scoped, "acme")) is True
    assert run(service._matches_exclusion(sigma, event_data, scoped, "other")) is False
    assert run(service._matches_exclusion(sigma, event_data, scoped, None)) is False

    unscoped = VeloSigmaExclusion(name="r", created_by="t", title=TITLE)
    assert run(service._matches_exclusion(sigma, event_data, unscoped, None)) is True


def test_extract_event_fields_matches_ingest_shape_for_powershell_context_info():
    event = {
        "System": {**SYSMON_EVENT["System"], "Channel": "Microsoft-Windows-PowerShell/Operational"},
        "EventData": {
            "MessageNumber": 1,
            "MessageTotal": 1,
            "ScriptBlockText": "Get-Process",
            "ScriptBlockId": "abc",
            "Path": "C:\\scripts\\ok.ps1",
            "ContextInfo": "        Severity = Informational\n        Host Application = C:\\Windows\\powershell.exe -File ok.ps1\n",
        },
        "Message": "x",
    }
    sigma = VelociraptorSigmaAlert(
        computer="H",
        channel="Microsoft-Windows-PowerShell/Operational",
        title="t",
        level="low",
        event=event,
        index_pattern="n/a",
        sourceRef="1",
    )
    fields = velo_sigma.extract_event_fields(sigma)
    assert fields["Host Application"] == "C:\\Windows\\powershell.exe -File ok.ps1"
    assert fields["hostApplication"] == fields["Host Application"]
    assert fields["ScriptBlockText"] == "Get-Process"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
