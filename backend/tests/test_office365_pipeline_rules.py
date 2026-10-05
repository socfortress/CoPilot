"""Office 365 pipeline rules CoPilot provisions (integrations/office365/services/provision.py).

- OFFICE365 PROCESSING PIPELINE named a rule, "SYSLOG TYPE OFFICE365", that provisioning never
  created (its creator was keyed "Office365 Syslog Type").
- "Office365 Timestamp - UTC" once read `data_office_365_CreationTime` (the field is
  `data_office365_CreationTime`). Rules are only created when missing, so that version stayed on
  existing Graylogs: no Office 365 document got `timestamp_utc` (lab, 2026-10-04). It is repaired on
  provisioning and once at CoPilot startup.

Graylog is faked; no network, no database.

Run with: cd backend && python -m pytest tests/test_office365_pipeline_rules.py
"""

import asyncio
import os
import re
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.graylog.schema.pipelines import PipelineRule  # noqa: E402
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse  # noqa: E402
from app.integrations.office365.schema.provision import PipelineRuleTitles  # noqa: E402
from app.integrations.office365.services import provision  # noqa: E402

OLD_TIMESTAMP_RULE = (
    'rule "Office365 Timestamp - UTC"\nwhen\n has_field("data_office_365_CreationTime")\nthen\n'
    ' let creation_time = $message.data_office_365_CreationTime;\n set_field("timestamp_utc", creation_time);\nend'
)


def _rule(title, source, rule_id=None):
    return PipelineRule(created_at="2024-01-01T00:00:00Z", id=rule_id or title, title=title, source=source, description=title)


class FakeGraylog:
    def __init__(self, rules, pipelines=("OFFICE365 PROCESSING PIPELINE",)):
        self.rules = {r.title: r for r in rules}
        self.pipelines = pipelines
        self.created, self.updated = [], []

    async def get_pipeline_rules(self):
        return PipelineRulesResponse(message="ok", success=True, pipeline_rules=list(self.rules.values()))

    async def get_pipelines(self):
        return SimpleNamespace(pipelines=[SimpleNamespace(title=t) for t in self.pipelines])

    async def create_pipeline_rule(self, rule):
        self.created.append(rule.title)
        self.rules[rule.title] = _rule(rule.title, rule.source)

    async def put(self, endpoint, data=None):
        self.updated.append((endpoint, data))
        return {"success": True, "data": None}


def _run(graylog, coro_factory):
    with patch.object(provision, "get_pipeline_rules", graylog.get_pipeline_rules), patch.object(
        provision,
        "get_pipelines",
        graylog.get_pipelines,
    ), patch.object(provision, "create_pipeline_rule", graylog.create_pipeline_rule), patch.object(
        provision,
        "send_graylog_put_request",
        graylog.put,
    ):
        return asyncio.run(coro_factory())


def test_every_rule_the_pipeline_names_is_one_provisioning_creates():
    created = {t.value for t in PipelineRuleTitles}
    captured = {}

    async def capture(pipeline):
        captured["source"] = pipeline.source

    with patch.object(provision, "create_pipeline_graylog", capture):
        asyncio.run(provision.create_office365_pipeline("OFFICE365 PROCESSING PIPELINE"))
    named = set(re.findall(r'rule "([^"]+)"', captured["source"]))
    assert named <= created, named - created


def test_a_missing_syslog_type_rule_is_created():
    graylog = FakeGraylog(
        [_rule(t.value, f'rule "{t.value}"\nwhen true\nthen\nend') for t in PipelineRuleTitles if t.value != "SYSLOG TYPE OFFICE365"],
    )
    _run(graylog, provision.check_pipeline_rules)
    assert graylog.created == ["SYSLOG TYPE OFFICE365"]
    assert 'set_field("syslog_type", "office365")' in graylog.rules["SYSLOG TYPE OFFICE365"].source


def test_the_old_timestamp_rule_is_repaired_and_a_correct_one_left_alone():
    rules = [_rule(t.value, f'rule "{t.value}"\nwhen true\nthen\nend') for t in PipelineRuleTitles]
    rules = [r for r in rules if r.title != "Office365 Timestamp - UTC"] + [_rule("Office365 Timestamp - UTC", OLD_TIMESTAMP_RULE, "r-ts")]
    graylog = FakeGraylog(rules)
    _run(graylog, provision.check_pipeline_rules)
    [(endpoint, data)] = graylog.updated
    assert endpoint == "/api/system/pipelines/rule/r-ts"
    assert "data_office365_CreationTime" in data["source"] and "data_office_365" not in data["source"]
    assert data["title"] == "Office365 Timestamp - UTC"

    fixed = FakeGraylog([_rule(t.value, provision.office365_utc_rule_source(t.value)) for t in PipelineRuleTitles])
    _run(fixed, provision.check_pipeline_rules)
    assert fixed.updated == [] and fixed.created == []


def test_startup_check_only_where_office365_is_in_use_and_never_raises():
    unused = FakeGraylog([_rule("Office365 Timestamp - UTC", OLD_TIMESTAMP_RULE)], pipelines=("SOMETHING ELSE",))
    _run(unused, provision.ensure_office365_pipeline_rules)
    assert unused.updated == [] and unused.created == []

    used = FakeGraylog([_rule("Office365 Timestamp - UTC", OLD_TIMESTAMP_RULE)])
    _run(used, provision.ensure_office365_pipeline_rules)
    assert len(used.updated) == 1 and "SYSLOG TYPE OFFICE365" in used.created

    async def unreachable():
        raise ConnectionError("Graylog is down")

    broken = FakeGraylog([])
    broken.get_pipelines = unreachable
    _run(broken, provision.ensure_office365_pipeline_rules)  # logged, not raised
