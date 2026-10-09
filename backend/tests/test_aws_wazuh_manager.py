"""The write path to the Wazuh manager's ossec.conf for AWS.

The Wazuh API only replaces ossec.conf as a whole, so this pins the guards around every write:
nothing is written from a stale copy, a file the manager does not validate is replaced by the
original before anything restarts, and the manager restarts only after a clean validation.

No network: the Wazuh API is a fake that records each call.

Run with: cd backend && python -m pytest tests/test_aws_wazuh_manager.py
"""

import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys  # noqa: E402
from app.integrations.aws.services import wazuh_manager  # noqa: E402
from app.integrations.aws.services.wazuh_config import desired_buckets  # noqa: E402

ORIGINAL = """<ossec_config>
  <global>
    <jsonout_output>yes</jsonout_output>
  </global>
</ossec_config>
"""


def run(coroutine):
    return asyncio.run(coroutine)


def auth_keys():
    return ProvisionAwsAuthKeys(
        ACCESS_KEY_ID="AKIAABCDEFGHIJKLMNOP",
        SECRET_ACCESS_KEY="the-secret",
        AWS_ACCOUNT_ID="123456789012",
        BUCKET_NAME="example-cloudtrail-logs",
        SERVICES="cloudtrail",
        ONLY_LOGS_AFTER="2026-OCT-08",
    )


class FakeManager:
    """Serves successive ossec.conf reads and records writes, validations and restarts."""

    def __init__(self, monkeypatch, reads, put_ok=True, valid=True, file_after_failed_put=None):
        self.reads = list(reads)
        self.file = self.reads[0]
        self.calls = []
        self.put_ok = put_ok
        self.valid = valid
        self.file_after_failed_put = file_after_failed_put

        async def get(endpoint, params=None, **kwargs):
            if endpoint == "/manager/configuration":
                self.calls.append("GET")
                self.file = self.reads.pop(0) if self.reads else self.file
                return {"success": True, "data": self.file}
            if endpoint == "/manager/configuration/validation":
                self.calls.append("VALIDATE")
                if self.valid:
                    return {
                        "success": True,
                        "data": {"data": {"affected_items": [{"name": "master", "status": "OK"}], "total_failed_items": 0}},
                    }
                return {
                    "success": True,
                    "data": {"data": {"affected_items": [], "failed_items": [{"error": 1125}], "total_failed_items": 1}},
                }
            raise AssertionError(f"unexpected GET {endpoint}")

        async def put(endpoint, data=None, **kwargs):
            if endpoint == "/manager/restart":
                self.calls.append("RESTART")
                return {"success": True, "data": {"error": 0}}
            text = data.decode("utf-8")
            first_write = not any(c.startswith("PUT") for c in self.calls)
            self.calls.append("PUT_ORIGINAL" if text == ORIGINAL else "PUT_NEW")
            if first_write and not self.put_ok:
                if self.file_after_failed_put is not None:
                    self.file = self.file_after_failed_put
                return {"success": False, "message": "HTTP error 400: invalid"}
            self.file = text
            return {"success": True, "data": {"error": 0}}

        monkeypatch.setattr(wazuh_manager, "send_get_request", get)
        monkeypatch.setattr(wazuh_manager, "send_put_request", put)


def apply(adopt_existing=False):
    keys = auth_keys()
    return run(wazuh_manager.apply_instance_buckets(desired_buckets(keys), keys.BUCKET_NAME, keys.AWS_ACCOUNT_ID, adopt_existing))


def test_a_clean_write_is_re_read_validated_then_restarted(monkeypatch):
    manager = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL])

    result = apply()

    assert result.changed
    assert manager.calls == ["GET", "GET", "PUT_NEW", "VALIDATE", "RESTART"]
    assert "example-cloudtrail-logs" in manager.file


def test_nothing_is_written_from_a_stale_copy(monkeypatch):
    """Someone else changed ossec.conf between the read and the write: start over from their file."""
    changed = ORIGINAL.replace("yes", "no")
    manager = FakeManager(monkeypatch, [ORIGINAL, changed, changed, changed])

    apply()

    assert manager.calls == ["GET", "GET", "GET", "GET", "PUT_NEW", "VALIDATE", "RESTART"]
    assert "<jsonout_output>no</jsonout_output>" in manager.file, "the other edit must survive"


def test_a_file_that_keeps_changing_is_never_written(monkeypatch):
    manager = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL + " ", ORIGINAL + "  ", ORIGINAL + "   "])

    with pytest.raises(HTTPException) as err:
        apply()

    assert err.value.status_code == 409
    assert not any(c.startswith("PUT") or c == "RESTART" for c in manager.calls)


def test_an_invalid_file_is_replaced_by_the_original_and_nothing_restarts(monkeypatch):
    manager = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL], valid=False)

    with pytest.raises(HTTPException) as err:
        apply()

    assert "restored" in err.value.detail
    assert manager.calls == ["GET", "GET", "PUT_NEW", "VALIDATE", "PUT_ORIGINAL"]
    assert manager.file == ORIGINAL


def test_a_refused_write_that_left_the_file_changed_is_put_back(monkeypatch):
    manager = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL], put_ok=False, file_after_failed_put="<ossec_config/>")

    with pytest.raises(HTTPException):
        apply()

    assert manager.calls[-1] == "PUT_ORIGINAL"
    assert manager.file == ORIGINAL
    assert "RESTART" not in manager.calls


def test_a_refused_write_that_left_the_file_alone_is_not_rewritten(monkeypatch):
    manager = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL], put_ok=False)

    with pytest.raises(HTTPException):
        apply()

    assert manager.calls == ["GET", "GET", "PUT_NEW", "GET"]
    assert "RESTART" not in manager.calls


def test_an_unchanged_configuration_is_neither_written_nor_restarted(monkeypatch):
    deployed = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL])
    apply()
    manager = FakeManager(monkeypatch, [deployed.file])

    result = apply(adopt_existing=True)

    assert not result.changed
    assert manager.calls == ["GET"]


def test_a_conflict_is_a_400_and_writes_nothing(monkeypatch):
    deployed = FakeManager(monkeypatch, [ORIGINAL, ORIGINAL])
    apply()
    manager = FakeManager(monkeypatch, [deployed.file])

    with pytest.raises(HTTPException) as err:
        apply(adopt_existing=False)

    assert err.value.status_code == 400
    assert manager.calls == ["GET"]


def test_the_exit_23_notice_always_carries_the_section_to_add():
    notice = wazuh_manager.aws_config_notice(detected=False, region="eu-west-1")

    assert notice.contents == "[default]\nregion = eu-west-1\n"
    assert "cannot read or write /root/.aws/config" in notice.summary
    assert wazuh_manager.aws_config_notice(detected=True, region=None).summary.startswith("Action required")
