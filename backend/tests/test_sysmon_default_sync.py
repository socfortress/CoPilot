r"""The SOCFortress default Sysmon config sync: this CoPilot pulls the signed default and stores it as its default.

What is pinned here:
* a valid release is applied (the content as is, sync.json, sync-status.json, an audit row with the system actor and
  none of the XML), and a later check sends the release it has and its ETag: a 304 changes nothing;
* every verification failure leaves the default and sync.json alone: a tampered manifest or content, an unknown or
  expired key, wrong formats or channel, every hash and size mismatch, no placeholder, a placeholder count that is
  wrong, a config validate_sysmon_config refuses, a schemaversion that is not the config's; and the manifest is never
  read before its signature checks out;
* anti-rollback against sync.json; the local-modification guard in "on", "force" (the env or Sync now) and "off";
  an equal stored default adopted (line endings aside);
* no license, no key configured, an unusable URL: nothing is fetched; every HTTP error, a network error, a redirect to
  another host, a compressed body and the 12 MiB cap each give their outcome; MinIO failures too;
* the job is registered and never raises; the routes resolve before /{customer_code}, are admin only, audit the admin;
* the license key never reaches a log line, a stored record or an audit row (its fingerprint does).

The configs below are small synthetic ones. The real default never belongs in this (public) repo.
No network, no database: the service is an httpx.MockTransport, MinIO and the audit write are fakes, the keys are
generated here.

Run with: cd backend && python -m pytest tests/test_sysmon_default_sync.py
"""

import asyncio
import base64
import functools
import hashlib
import inspect
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import Encoding  # noqa: E402
from cryptography.hazmat.primitives.serialization import PublicFormat  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from loguru import logger  # noqa: E402
from miniopy_async.error import S3Error  # noqa: E402

import app.active_response.routes.sysmon_config as routes  # noqa: E402
import app.active_response.services.sysmon_default_sync as sync  # noqa: E402
import app.data_store.data_store_operations as store  # noqa: E402
from app.active_response.schema.sysmon_config import (  # noqa: E402
    SysmonDefaultConfigSaveRequest,
)
from app.active_response.schema.sysmon_default_sync import SyncOutcome  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditResult  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402

BUCKET = "sysmon-config-defaults"
DEFAULT = "sysmon_config.xml"
SYNC = "sync.json"
STATUS = "sync-status.json"
SERVICE = "https://sync.test"
BUNDLE_URL = f"{SERVICE}/v1/sysmon/default"
LICENSE_KEY = "LICENSE-abcdef-0123456789-SECRET"
FINGERPRINT = hashlib.sha256(LICENSE_KEY.encode()).hexdigest()[:12]
ADMIN = SimpleNamespace(id=7, username="alice", role_id=RoleEnum.admin.value)

TEMPLATE = b"""<Sysmon schemaversion="4.90">
  <EventFiltering>
    <RuleGroup name="" groupRelation="or">
      <ProcessCreate onmatch="exclude">
        <ParentImage condition="is">C:\\Program Files\\__INSTALLDIRNAME__\\chainsaw\\chainsaw.exe</ParentImage>
        <Image condition="is">C:\\Program Files\\__INSTALLDIRNAME__\\tool.exe</Image>
      </ProcessCreate>
    </RuleGroup>
  </EventFiltering>
</Sysmon>
"""
NEWER = TEMPLATE.replace(b"tool.exe", b"tool2.exe")
NEWEST = TEMPLATE.replace(b"tool.exe", b"tool3.exe")
# What an admin saved by hand
LOCAL = TEMPLATE.replace(b"tool.exe", b"mine.exe")

KEY = Ed25519PrivateKey.generate()
OTHER_KEY = Ed25519PrivateKey.generate()
KEY_ID = "sysmon-release-test"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def public_b64(private) -> str:
    return b64(private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_for(content: bytes, sequence: int = 1, **overrides) -> dict:
    manifest = {
        "format": "socfortress-sysmon-default/1",
        "key_id": KEY_ID,
        "channel": "stable",
        "sequence": sequence,
        "commit": f"{sequence:x}".rjust(40, "a"),
        "created_at": "2026-11-20T12:00:00Z",
        "content_sha256": sha(content),
        "content_sha256_crlf": sha(sync.crlf(content)),
        "content_size": len(content),
        "placeholders": content.count(b"__INSTALLDIRNAME__"),
        "schemaversion": "4.90",
        "an_unknown_field": "ignored",
    }
    manifest.update(overrides)
    return manifest


def canonical(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def bundle(
    content: bytes = TEMPLATE,
    sequence: int = 1,
    *,
    key=KEY,
    manifest: dict = None,
    manifest_bytes: bytes = None,
    signature: bytes = None,
    shipped_content: bytes = None,
    bundle_format: str = "socfortress-sysmon-default-bundle/1",
    **overrides,
) -> bytes:
    """A release bundle as the installer's release workflow makes it; every part can be replaced to break it."""
    if manifest_bytes is None:
        manifest_bytes = canonical(manifest if manifest is not None else manifest_for(content, sequence, **overrides))
    if signature is None:
        signature = key.sign(manifest_bytes)
    return json.dumps(
        {
            "bundle_format": bundle_format,
            "manifest": b64(manifest_bytes),
            "signature": b64(signature),
            "content": b64(shipped_content if shipped_content is not None else content),
        },
    ).encode()


def ok(body: bytes, sequence: int = 1, content: bytes = TEMPLATE) -> httpx.Response:
    return httpx.Response(200, content=body, headers={"ETag": f'"{sequence}-{sha(content)}"', "Cache-Control": "no-store"})


# --------------------------------------------------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------------------------------------------------


class _Object:
    def __init__(self, content):
        self.content = content

    async def read(self):
        return self.content

    def close(self):
        pass


class FakeMinio:
    """The sysmon-config-defaults bucket in memory, with failures on demand."""

    def __init__(self):
        self.objects = {}
        self.puts = []
        self.fail_get = None
        self.fail_put = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_object(self, bucket_name, object_name):
        if self.fail_get is not None:
            raise self.fail_get
        if (bucket_name, object_name) not in self.objects:
            raise S3Error("NoSuchKey", "stub", f"/{bucket_name}/{object_name}", None, None, None)
        return _Object(self.objects[(bucket_name, object_name)])

    async def put_object(self, bucket_name, object_name, data, length, content_type):
        if object_name in self.fail_put:
            raise self.fail_put[object_name]
        content = data.read()
        assert len(content) == length
        self.objects[(bucket_name, object_name)] = content
        self.puts.append(object_name)

    def get(self, name):
        return self.objects.get((BUCKET, name))

    def put(self, name, content: bytes):
        self.objects[(BUCKET, name)] = content

    def json(self, name):
        raw = self.get(name)
        return None if raw is None else json.loads(raw)


class Service:
    """The SOCFortress sync service: answers in turn (the last one repeats), every request kept."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer(request) if callable(answer) else answer

    @property
    def transport(self):
        return httpx.MockTransport(self.handle)


@pytest.fixture
def env(monkeypatch, tmp_path):
    keys_file = tmp_path / "release_keys.json"
    keys_file.write_text(json.dumps({"keys": [{"key_id": KEY_ID, "public_key": public_b64(KEY), "not_after": "2099-12-31T23:59:59Z"}]}))
    monkeypatch.setattr(sync, "TRUSTED_KEYS_FILE", keys_file)
    monkeypatch.setenv("SOCFORTRESS_SYSMON_SYNC_URL", SERVICE)
    monkeypatch.delenv("SYSMON_DEFAULT_SYNC", raising=False)
    minio = FakeMinio()
    monkeypatch.setattr(store, "create_session", AsyncMock(return_value=minio))
    monkeypatch.setattr(store, "create_bucket_if_not_exists", AsyncMock())
    license_lookup = AsyncMock(return_value=SimpleNamespace(license_key=LICENSE_KEY))
    monkeypatch.setattr(sync, "get_license", license_lookup)
    return SimpleNamespace(minio=minio, keys_file=keys_file, license=license_lookup)


def check(service: Service, force: bool = False, actor=None):
    return asyncio.run(sync.run_sysmon_default_sync(None, force=force, actor=actor, transport=service.transport))


def sync_rows(audit_rows):
    return [row for row in audit_rows if row.action == AuditAction.SYSMON_DEFAULT_SYNC.value]


def applied_once(env, audit_rows, content=TEMPLATE, sequence=1):
    """A CoPilot that has synced release <sequence>."""
    result = check(Service(ok(bundle(content, sequence), sequence, content)))
    assert result.outcome == SyncOutcome.APPLIED, result.message
    env.minio.puts.clear()
    audit_rows.clear()


# --------------------------------------------------------------------------------------------------------------------
# A valid release
# --------------------------------------------------------------------------------------------------------------------


def test_a_valid_release_is_stored_as_the_default(env, audit_rows):
    service = Service(ok(bundle()))
    result = check(service)

    assert result.outcome == SyncOutcome.APPLIED and result.ok
    assert (result.sequence, result.commit) == (1, "1".rjust(40, "a"))
    assert env.minio.get(DEFAULT) == TEMPLATE
    record = env.minio.json(SYNC)
    assert record["sequence"] == 1 and record["commit"] == "1".rjust(40, "a")
    assert record["content_sha256"] == sha(TEMPLATE) and record["content_sha256_crlf"] == sha(TEMPLATE.replace(b"\n", b"\r\n"))
    assert record["key_id"] == KEY_ID and record["source"] == "socfortress-sync" and record["service_url"] == SERVICE
    assert record["applied_at"] == result.checked_at
    # The content first, the record after it
    assert env.minio.puts == [DEFAULT, SYNC, STATUS]
    assert env.minio.json(STATUS)["outcome"] == "applied"

    (request,) = service.requests
    assert str(request.url) == BUNDLE_URL and request.method == "GET"
    assert request.headers["x-api-key"] == LICENSE_KEY and request.headers["module-version"] == "1.0"
    assert "if-none-match" not in request.headers and "x-sysmon-default-sequence" not in request.headers


def test_the_apply_is_audited_with_the_system_actor_and_none_of_the_xml(env, audit_rows):
    check(Service(ok(bundle())))
    (row,) = sync_rows(audit_rows)
    assert row.action == "response.sysmon_default_sync" and row.result == AuditResult.SUCCESS.value
    assert (row.actor_user_id, row.actor_username, row.customer_code) == (None, "system", None)
    assert row.entity_id == "sysmon-config-defaults/sysmon_config.xml"
    assert row.new_value["sequence"] == 1 and row.new_value["content_sha256"] == sha(TEMPLATE)
    assert row.new_value["outcome"] == "applied" and row.new_value["forced"] is False
    assert row.old_value == {"sequence": None, "commit": None, "content_sha256": None}
    stored = json.dumps(row.model_dump(), default=str)
    assert "chainsaw" not in stored and "<Sysmon" not in stored and LICENSE_KEY not in stored


def test_the_next_check_sends_its_release_and_a_304_changes_nothing(env, audit_rows):
    applied_once(env, audit_rows)
    service = Service(httpx.Response(304))
    result = check(service)

    assert result.outcome == SyncOutcome.UP_TO_DATE and result.ok
    (request,) = service.requests
    assert request.headers["x-sysmon-default-sequence"] == "1"
    assert request.headers["if-none-match"] == f'"1-{sha(TEMPLATE)}"'
    assert env.minio.puts == [STATUS] and env.minio.get(DEFAULT) == TEMPLATE
    assert sync_rows(audit_rows) == []


def test_a_newer_release_replaces_the_synced_default(env, audit_rows):
    applied_once(env, audit_rows)
    result = check(Service(ok(bundle(NEWER, 2), 2, NEWER)))

    assert result.outcome == SyncOutcome.APPLIED and result.sequence == 2
    assert env.minio.get(DEFAULT) == NEWER and env.minio.json(SYNC)["sequence"] == 2
    (row,) = sync_rows(audit_rows)
    assert row.old_value == {"sequence": 1, "commit": "1".rjust(40, "a"), "content_sha256": sha(TEMPLATE)}
    assert row.new_value["sequence"] == 2 and row.new_value["forced"] is False


def test_unknown_manifest_fields_are_ignored_and_a_crlf_release_is_fine(env, audit_rows):
    crlf_template = TEMPLATE.replace(b"\n", b"\r\n")
    result = check(Service(ok(bundle(crlf_template))))
    assert result.outcome == SyncOutcome.APPLIED and env.minio.get(DEFAULT) == crlf_template


# --------------------------------------------------------------------------------------------------------------------
# Verification failures: nothing changes
# --------------------------------------------------------------------------------------------------------------------


def _tampered_manifest():
    signed = canonical(manifest_for(TEMPLATE))
    return bundle(manifest_bytes=canonical(manifest_for(TEMPLATE, sequence=99)), signature=KEY.sign(signed))


REFUSALS = {
    "tampered manifest": (_tampered_manifest(), "does not verify"),
    "tampered content": (bundle(shipped_content=TEMPLATE.replace(b"tool.exe", b"evil.exe")), "SHA-256 is not the one"),
    "unknown key": (bundle(key=OTHER_KEY), "does not verify"),
    "no signature bytes": (bundle(signature=b"\x00" * 64), "does not verify"),
    "short signature": (bundle(signature=b"\x01" * 63), "64-byte"),
    "wrong bundle format": (bundle(bundle_format="socfortress-sysmon-default-bundle/2"), "unknown bundle format"),
    "wrong manifest format": (bundle(format="socfortress-sysmon-default/2"), "unknown manifest format"),
    "another key's id": (bundle(key_id="sysmon-release-other"), "names release key 'sysmon-release-other'"),
    "a malformed key id": (bundle(key_id="bad key/id"), "'key_id' is missing or malformed"),
    "another channel": (bundle(channel="beta"), "channel 'beta'"),
    "sequence 0": (bundle(sequence=0), "positive integer"),
    "sequence true": (bundle(manifest=manifest_for(TEMPLATE, sequence=True)), "'sequence' is not an integer"),
    "short commit": (bundle(commit="abc123"), "'commit' is missing or malformed"),
    "local created_at": (bundle(created_at="2026-11-20T12:00:00+01:00"), "'created_at' is missing or malformed"),
    "content hash": (bundle(content_sha256="0" * 64), "SHA-256 is not the one"),
    "crlf hash": (bundle(content_sha256_crlf="0" * 64), "CRLF SHA-256"),
    "size": (bundle(content_size=len(TEMPLATE) + 1), "the signed manifest says"),
    "placeholders 0": (
        bundle(TEMPLATE.replace(b"__INSTALLDIRNAME__", b"socfortress"), placeholders=0),
        "no __INSTALLDIRNAME__ placeholder",
    ),
    "placeholder count": (bundle(placeholders=3), "the signed manifest says 3"),
    "schemaversion": (bundle(schemaversion="4.91"), "schemaversion '4.91'"),
    "not json": (b"<html>maintenance</html>", "not JSON"),
    "not a bundle": (b"[1, 2]", "not a release bundle"),
    "content not base64": (
        json.dumps({"bundle_format": "socfortress-sysmon-default-bundle/1", "manifest": "", "signature": "", "content": "%%"}).encode(),
        "not valid base64",
    ),
}


@pytest.mark.parametrize("name", list(REFUSALS))
def test_a_bundle_that_fails_verification_changes_nothing(env, audit_rows, name):
    body, reason = REFUSALS[name]
    env.minio.put(DEFAULT, LOCAL)
    result = check(Service(ok(body)))

    assert result.outcome == SyncOutcome.VERIFICATION_FAILED and not result.ok
    assert reason in result.message and "Nothing was changed" in result.message
    assert env.minio.get(DEFAULT) == LOCAL and env.minio.get(SYNC) is None
    assert env.minio.puts == [STATUS] and env.minio.json(STATUS)["outcome"] == "verification_failed"
    assert sync_rows(audit_rows) == []


def test_an_expired_key_is_not_trusted(env, audit_rows):
    env.keys_file.write_text(json.dumps({"keys": [{"key_id": KEY_ID, "public_key": public_b64(KEY), "not_after": "2020-01-01T00:00:00Z"}]}))
    result = check(Service(ok(bundle())))
    assert result.outcome == SyncOutcome.VERIFICATION_FAILED
    assert "expired on 2020-01-01T00:00:00Z" in result.message and env.minio.get(DEFAULT) is None


def test_the_manifest_is_not_read_before_the_signature_checks_out(env, audit_rows):
    # Not JSON, and not signed by a trusted key: the refusal is the signature's, never the manifest's
    result = check(Service(ok(bundle(manifest_bytes=b"{not json", key=OTHER_KEY))))
    assert "does not verify" in result.message and "not JSON" not in result.message


@pytest.mark.parametrize(
    "content, reason",
    [
        (b"<Sysmon><EventFiltering>__INSTALLDIRNAME__", "Invalid XML syntax"),
        (b'<NotSysmon schemaversion="4.90">__INSTALLDIRNAME__</NotSysmon>', "Root element must be 'Sysmon'"),
        (
            b'<Sysmon schemaversion="4.90"><EventFiltering><RuleGroup name="__INSTALLDIRNAME__" groupRelation="or"/></EventFiltering></Sysmon>',
            "no event filters",
        ),
        (b"\xff\xfe__INSTALLDIRNAME__", "not UTF-8"),
    ],
)
def test_a_signed_config_validate_sysmon_config_refuses_is_not_applied(env, audit_rows, content, reason):
    result = check(Service(ok(bundle(content))))
    assert result.outcome == SyncOutcome.INVALID_CONFIG and reason in result.message
    assert env.minio.get(DEFAULT) is None and env.minio.get(SYNC) is None


def test_a_signed_config_over_5_mib_is_not_applied(env, audit_rows):
    big = TEMPLATE.replace(b"<EventFiltering>", b"<!-- " + b"x" * (5 * 1024 * 1024) + b" --><EventFiltering>")
    result = check(Service(ok(bundle(big))))
    assert result.outcome == SyncOutcome.INVALID_CONFIG and "5 MiB" in result.message


# --------------------------------------------------------------------------------------------------------------------
# Anti-rollback
# --------------------------------------------------------------------------------------------------------------------


def test_an_older_release_is_refused(env, audit_rows):
    applied_once(env, audit_rows, NEWER, 5)
    result = check(Service(ok(bundle(TEMPLATE, 4))))
    assert result.outcome == SyncOutcome.ROLLBACK_REFUSED and "older than SOCFortress release #5" in result.message
    assert env.minio.get(DEFAULT) == NEWER and env.minio.json(SYNC)["sequence"] == 5


def test_the_same_sequence_with_another_content_is_refused(env, audit_rows):
    applied_once(env, audit_rows, NEWER, 5)
    result = check(Service(ok(bundle(TEMPLATE, 5))))
    assert result.outcome == SyncOutcome.ROLLBACK_REFUSED and "different content" in result.message
    assert env.minio.get(DEFAULT) == NEWER


def test_force_never_bypasses_anti_rollback(env, audit_rows):
    applied_once(env, audit_rows, NEWER, 5)
    env.minio.put(DEFAULT, LOCAL)
    result = check(Service(ok(bundle(TEMPLATE, 4))), force=True)
    assert result.outcome == SyncOutcome.ROLLBACK_REFUSED and env.minio.get(DEFAULT) == LOCAL


def test_the_same_release_again_is_a_no_op(env, audit_rows):
    applied_once(env, audit_rows)
    # Forced, so no ETag is sent and the service answers with the bundle
    result = check(Service(ok(bundle())), force=True)
    assert result.outcome == SyncOutcome.UP_TO_DATE and env.minio.puts == [STATUS]
    assert sync_rows(audit_rows) == []


# --------------------------------------------------------------------------------------------------------------------
# The local-modification guard
# --------------------------------------------------------------------------------------------------------------------


def test_a_default_changed_here_is_not_overwritten(env, audit_rows):
    applied_once(env, audit_rows)
    env.minio.put(DEFAULT, LOCAL)  # an admin's "Save as default"
    service = Service(ok(bundle(NEWER, 2), 2, NEWER))
    result = check(service)

    assert result.outcome == SyncOutcome.LOCAL_DEFAULT_DIFFERS and result.sequence == 2
    assert "changed here since SOCFortress release #1 was synced" in result.message
    assert "SOCFortress release #2" in result.message
    assert env.minio.get(DEFAULT) == LOCAL and env.minio.json(SYNC)["sequence"] == 1
    # It needs the bundle to say which release it differs from: no ETag
    assert "if-none-match" not in service.requests[0].headers
    assert sync_rows(audit_rows) == []


def test_a_default_set_before_sync_is_not_overwritten(env, audit_rows):
    env.minio.put(DEFAULT, LOCAL)
    result = check(Service(ok(bundle())))
    assert result.outcome == SyncOutcome.LOCAL_DEFAULT_DIFFERS and "was not applied" in result.message
    assert env.minio.get(DEFAULT) == LOCAL and env.minio.get(SYNC) is None


def test_an_equal_default_is_adopted_without_rewriting_it(env, audit_rows):
    env.minio.put(DEFAULT, TEMPLATE)
    result = check(Service(ok(bundle())))
    assert result.outcome == SyncOutcome.ADOPTED and result.ok
    assert env.minio.puts == [SYNC, STATUS] and env.minio.json(SYNC)["sequence"] == 1
    (row,) = sync_rows(audit_rows)
    assert row.new_value["outcome"] == "adopted"


def test_line_endings_alone_are_no_local_change(env, audit_rows):
    # The editor turns CRLF into LF: a default an admin re-saved unchanged is still the release
    crlf_template = TEMPLATE.replace(b"\n", b"\r\n")
    env.minio.put(DEFAULT, TEMPLATE)
    assert check(Service(ok(bundle(crlf_template)))).outcome == SyncOutcome.ADOPTED
    assert env.minio.get(DEFAULT) == TEMPLATE

    newer = NEWER.replace(b"\n", b"\r\n")
    assert check(Service(ok(bundle(newer, 2), 2, newer))).outcome == SyncOutcome.APPLIED
    assert env.minio.get(DEFAULT) == newer


def test_force_from_the_environment_overwrites_a_default_changed_here(env, audit_rows, monkeypatch):
    applied_once(env, audit_rows)
    env.minio.put(DEFAULT, LOCAL)
    monkeypatch.setenv("SYSMON_DEFAULT_SYNC", "force")
    service = Service(ok(bundle(NEWER, 2), 2, NEWER))
    result = check(service)

    assert result.outcome == SyncOutcome.APPLIED and result.forced and result.mode.value == "force"
    assert "which had been changed here" in result.message
    assert env.minio.get(DEFAULT) == NEWER
    (row,) = sync_rows(audit_rows)
    assert row.new_value["forced"] is True and row.old_value["content_sha256"] == sha(LOCAL)


def test_a_forced_sync_now_restores_the_release(env, audit_rows):
    applied_once(env, audit_rows)
    env.minio.put(DEFAULT, LOCAL)
    result = check(Service(ok(bundle())), force=True, actor=ADMIN)
    assert result.outcome == SyncOutcome.APPLIED and env.minio.get(DEFAULT) == TEMPLATE
    (row,) = sync_rows(audit_rows)
    assert (row.actor_user_id, row.actor_username) == (7, "alice") and row.details == "Sync now"


def test_a_missing_default_is_restored(env, audit_rows):
    applied_once(env, audit_rows)
    del env.minio.objects[(BUCKET, DEFAULT)]
    service = Service(ok(bundle()))
    result = check(service)
    assert result.outcome == SyncOutcome.APPLIED and env.minio.get(DEFAULT) == TEMPLATE
    assert "if-none-match" not in service.requests[0].headers


@pytest.mark.parametrize("value", ["off", "OFF", "false", "0", "disabled"])
def test_off_never_fetches(env, audit_rows, monkeypatch, value):
    monkeypatch.setenv("SYSMON_DEFAULT_SYNC", value)
    service = Service(AssertionError("no request may be made"))
    result = check(service, force=True)
    assert result.outcome == SyncOutcome.OFF and service.requests == []
    assert env.minio.puts == [] and not env.license.await_count


def test_an_unknown_mode_runs_as_on_and_says_so(env, monkeypatch):
    monkeypatch.setenv("SYSMON_DEFAULT_SYNC", "sometimes")
    assert sync.sync_mode() == (sync.SyncMode.ON, "sometimes")
    status = asyncio.run(sync.get_sync_status())
    assert status.mode.value == "on" and status.mode_setting == "sometimes"


# --------------------------------------------------------------------------------------------------------------------
# Nothing to send with, nowhere to send it
# --------------------------------------------------------------------------------------------------------------------


def test_no_license_fetches_nothing(env):
    env.license.return_value = None
    service = Service(AssertionError("no request may be made"))
    result = check(service)
    assert result.outcome == SyncOutcome.NO_LICENSE and service.requests == []
    assert env.minio.json(STATUS)["outcome"] == "no_license"


def test_no_trusted_key_fetches_nothing(env):
    env.keys_file.write_text('{"keys": []}')
    service = Service(AssertionError("no request may be made"))
    result = check(service)
    assert result.outcome == SyncOutcome.NOT_CONFIGURED and service.requests == []
    assert not env.license.await_count


def test_the_shipped_trust_list_is_empty_for_now():
    assert json.loads(sync.TRUSTED_KEYS_FILE.read_text()) == {"keys": []}
    assert sync.load_trusted_keys() == []


def test_a_broken_trust_entry_never_widens_trust(env):
    env.keys_file.write_text(
        json.dumps(
            {
                "keys": [
                    {"key_id": "bad key", "public_key": public_b64(OTHER_KEY)},
                    {"key_id": "short", "public_key": b64(b"x" * 31)},
                    {"key_id": "not-b64", "public_key": "%%%"},
                    {"key_id": "when", "public_key": public_b64(OTHER_KEY), "not_after": "2099-12-31"},
                    {"key_id": KEY_ID, "public_key": public_b64(KEY)},
                    {"key_id": KEY_ID, "public_key": public_b64(OTHER_KEY)},
                ],
            },
        ),
    )
    assert [key.key_id for key in sync.load_trusted_keys()] == [KEY_ID]
    env.keys_file.write_text("not json")
    assert sync.load_trusted_keys() == []


@pytest.mark.parametrize(
    "url",
    ["http://sync.example.com", "ftp://sync.test", "https://user:pw@sync.test", "https://sync.test?x=1", "not a url"],
)
def test_an_unusable_service_url_fetches_nothing(env, monkeypatch, url):
    monkeypatch.setenv("SOCFORTRESS_SYSMON_SYNC_URL", url)
    service = Service(AssertionError("no request may be made"))
    result = check(service)
    assert result.outcome == SyncOutcome.INVALID_URL and service.requests == []


def test_the_service_url_defaults_and_plain_http_is_only_for_this_host(monkeypatch):
    monkeypatch.delenv("SOCFORTRESS_SYSMON_SYNC_URL", raising=False)
    assert sync.service_url() == "https://sysmon-sync.socfortress.co"
    assert sync._bundle_url("http://127.0.0.1:8080") == ("http://127.0.0.1:8080/v1/sysmon/default", None)
    monkeypatch.setenv("SOCFORTRESS_SYSMON_SYNC_URL", "https://sync.example.com/base/")
    assert sync._bundle_url(sync.service_url())[0] == "https://sync.example.com/base/v1/sysmon/default"


# --------------------------------------------------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, outcome, text",
    [
        (401, SyncOutcome.UNAUTHORIZED, "HTTP 401"),
        (403, SyncOutcome.LICENSE_REJECTED, "rejected this CoPilot's license"),
        (404, SyncOutcome.NOT_PUBLISHED, "has not published"),
        (429, SyncOutcome.RATE_LIMITED, "retry after 120 seconds"),
        (503, SyncOutcome.SERVICE_UNAVAILABLE, "HTTP 503"),
        (500, SyncOutcome.HTTP_ERROR, "HTTP 500"),
    ],
)
def test_each_http_error_has_its_outcome(env, audit_rows, status, outcome, text):
    env.minio.put(DEFAULT, LOCAL)
    result = check(Service(httpx.Response(status, headers={"Retry-After": "120"}, json={"detail": "x"})))
    assert result.outcome == outcome and text in result.message and not result.ok
    assert env.minio.get(DEFAULT) == LOCAL and env.minio.json(STATUS)["outcome"] == outcome.value


def test_a_network_error_is_reported(env):
    result = check(Service(httpx.ConnectError("connection refused")))
    assert result.outcome == SyncOutcome.NETWORK_ERROR and "ConnectError: connection refused" in result.message


def test_a_redirect_to_another_host_is_not_followed(env):
    def answer(request):
        if request.url.host == "sync.test":
            return httpx.Response(302, headers={"Location": "https://elsewhere.test/v1/sysmon/default"})
        raise AssertionError("the license key went to another host")

    service = Service(answer)
    result = check(service)
    assert result.outcome == SyncOutcome.REDIRECT_REFUSED and "elsewhere.test" in result.message
    assert [r.url.host for r in service.requests] == ["sync.test"]


def test_a_redirect_to_plain_http_on_the_same_host_is_not_followed(env):
    result = check(Service(httpx.Response(301, headers={"Location": "http://sync.test/v1/sysmon/default"})))
    assert result.outcome == SyncOutcome.REDIRECT_REFUSED


def test_a_redirect_within_the_service_is_followed(env):
    def answer(request):
        if request.url.path == "/v1/sysmon/default":
            return httpx.Response(307, headers={"Location": "/v1/sysmon/default/stable"})
        return ok(bundle())

    service = Service(answer)
    assert check(service).outcome == SyncOutcome.APPLIED
    assert [r.url.path for r in service.requests] == ["/v1/sysmon/default", "/v1/sysmon/default/stable"]
    assert service.requests[1].headers["x-api-key"] == LICENSE_KEY


def test_a_compressed_body_is_refused(env):
    result = check(Service(httpx.Response(200, content=b"\x1f\x8b", headers={"Content-Encoding": "gzip"})))
    assert result.outcome == SyncOutcome.HTTP_ERROR and "compressed" in result.message


def test_an_answer_over_12_mib_is_refused_by_its_length(env):
    result = check(Service(httpx.Response(200, content=b"x" * (12 * 1024 * 1024 + 1))))
    assert result.outcome == SyncOutcome.TOO_LARGE and "12 MiB" in result.message


def test_an_answer_over_12_mib_is_cut_off_without_a_length(env):
    chunks_sent = []

    class Endless(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(100):
                chunks_sent.append(1)
                yield b"x" * (1024 * 1024)

    result = check(Service(lambda request: httpx.Response(200, stream=Endless())))
    assert result.outcome == SyncOutcome.TOO_LARGE
    assert len(chunks_sent) == 13


# --------------------------------------------------------------------------------------------------------------------
# MinIO failures
# --------------------------------------------------------------------------------------------------------------------


def test_a_default_that_cannot_be_read_fetches_nothing(env):
    env.minio.fail_get = ConnectionError("MinIO is down")
    service = Service(AssertionError("no request may be made"))
    result = check(service)
    assert result.outcome == SyncOutcome.STORE_ERROR and "MinIO is down" in result.message and service.requests == []


def test_a_default_that_cannot_be_stored_is_audited_as_a_failure_and_not_recorded(env, audit_rows):
    env.minio.fail_put[DEFAULT] = ConnectionError("disk full")
    result = check(Service(ok(bundle())))
    assert result.outcome == SyncOutcome.STORE_ERROR and "disk full" in result.message
    assert env.minio.get(SYNC) is None
    (row,) = sync_rows(audit_rows)
    assert row.result == AuditResult.FAILURE.value and "disk full" in row.details


def test_a_record_that_cannot_be_written_is_adopted_by_the_next_check(env, audit_rows):
    env.minio.fail_put[SYNC] = ConnectionError("flaky")
    first = check(Service(ok(bundle())))
    assert first.outcome == SyncOutcome.STORE_ERROR and env.minio.get(DEFAULT) == TEMPLATE
    env.minio.fail_put.clear()
    assert check(Service(ok(bundle()))).outcome == SyncOutcome.ADOPTED
    assert env.minio.json(SYNC)["sequence"] == 1


def test_a_corrupt_sync_record_counts_as_none(env, audit_rows):
    env.minio.put(SYNC, b"{broken")
    env.minio.put(DEFAULT, LOCAL)
    assert check(Service(ok(bundle()))).outcome == SyncOutcome.LOCAL_DEFAULT_DIFFERS


def test_a_check_never_raises(env, monkeypatch):
    monkeypatch.setattr(sync, "_check", AsyncMock(side_effect=RuntimeError("bug")))
    result = check(Service(ok(bundle())))
    assert result.outcome == SyncOutcome.ERROR and "RuntimeError: bug" in result.message


# --------------------------------------------------------------------------------------------------------------------
# The license key stays secret
# --------------------------------------------------------------------------------------------------------------------


def test_the_license_key_never_reaches_a_log_a_record_or_an_audit_row(env, audit_rows):
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
    try:
        check(Service(httpx.Response(403)))
        check(Service(httpx.ConnectError("refused")))
        check(Service(ok(bundle(key=OTHER_KEY))))
        check(Service(ok(bundle())))
        check(Service(httpx.Response(304)))
    finally:
        logger.remove(sink)
    text = "\n".join(lines)
    assert LICENSE_KEY not in text and FINGERPRINT in text
    for (_, name), content in env.minio.objects.items():
        assert LICENSE_KEY.encode() not in content, name
    for row in audit_rows:
        assert LICENSE_KEY not in json.dumps(row.model_dump(), default=str)


def test_an_error_that_quotes_the_license_key_is_scrubbed(env, monkeypatch):
    # h11 quotes an illegal header value in its error; nothing may carry it on
    result = check(Service(httpx.LocalProtocolError(f"Illegal header value b'{LICENSE_KEY}'")))
    assert result.outcome == SyncOutcome.NETWORK_ERROR and LICENSE_KEY not in result.message
    assert f"[license key {FINGERPRINT}]" in result.message
    assert LICENSE_KEY.encode() not in env.minio.get(STATUS)

    monkeypatch.setattr(sync, "_fetch", AsyncMock(side_effect=ValueError(f"bad {LICENSE_KEY}")))
    result = check(Service(ok(bundle())))
    assert result.outcome == SyncOutcome.ERROR and LICENSE_KEY not in result.message


# --------------------------------------------------------------------------------------------------------------------
# Status, routes and the job
# --------------------------------------------------------------------------------------------------------------------


def test_the_status_says_when_the_default_was_changed_here(env, audit_rows):
    applied_once(env, audit_rows)
    status = asyncio.run(sync.get_sync_status())
    assert status.configured and status.trusted_key_ids == [KEY_ID] and status.service_url == SERVICE
    assert status.applied.sequence == 1 and status.default_present and status.local_default_differs is False
    assert status.last_check.outcome == SyncOutcome.APPLIED

    # An admin's "Save as default", through the real route: it still works, and sync leaves it alone afterwards
    body = SysmonDefaultConfigSaveRequest(config_content=LOCAL.decode())
    saved = asyncio.run(routes.save_sysmon_default_config(body, request=None, current_user=ADMIN))
    assert saved.success and env.minio.get(DEFAULT) == LOCAL
    assert asyncio.run(sync.get_sync_status()).local_default_differs is True
    assert check(Service(ok(bundle(NEWER, 2), 2, NEWER))).outcome == SyncOutcome.LOCAL_DEFAULT_DIFFERS
    assert env.minio.get(DEFAULT) == LOCAL


def test_the_status_reports_a_store_it_cannot_read(env):
    env.minio.fail_get = ConnectionError("MinIO is down")
    status = asyncio.run(sync.get_sync_status())
    assert status.read_error and "MinIO" in status.read_error and status.default_present is None


def test_sync_now_runs_a_check_as_the_admin(env, audit_rows, monkeypatch):
    service = Service(ok(bundle()))
    monkeypatch.setattr(routes, "run_sysmon_default_sync", functools.partial(sync.run_sysmon_default_sync, transport=service.transport))
    response = asyncio.run(routes.run_sysmon_default_sync_now(request=None, force=False, current_user=ADMIN, session=None))
    assert response.success and response.result.outcome == SyncOutcome.APPLIED
    assert response.status.applied.sequence == 1 and response.status.local_default_differs is False
    (row,) = sync_rows(audit_rows)
    assert (row.actor_user_id, row.actor_username) == (7, "alice")

    got = asyncio.run(routes.get_sysmon_default_sync_status())
    assert got.success and got.status.last_check.outcome == SyncOutcome.APPLIED


SYNC_PATH = "/api/sysmon_config/default-config/sync"


def _app():
    import copilot

    return copilot.app


def _resolve(method, path):
    from starlette.routing import Match

    scope = {"type": "http", "method": method, "path": path, "root_path": "", "query_string": b"", "headers": []}
    for route in _app().router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "endpoint", None)
    return None


def test_the_sync_routes_are_not_taken_for_a_customer_code():
    assert _resolve("GET", SYNC_PATH) is routes.get_sysmon_default_sync_status
    assert _resolve("POST", SYNC_PATH) is routes.run_sysmon_default_sync_now
    assert _resolve("GET", "/api/sysmon_config/default-config") is routes.get_sysmon_default_config
    assert _resolve("GET", "/api/sysmon_config/acme") is routes.get_customer_sysmon_config


def _required_scopes(dependant) -> set:
    scopes = set(getattr(dependant, "own_oauth_scopes", None) or [])
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            try:
                required = inspect.getclosurevars(dependency.call).nonlocals.get("required_scopes")
            except TypeError:
                required = None
            if isinstance(required, tuple):
                scopes |= set(required)
        scopes |= _required_scopes(dependency)
    return scopes


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_the_sync_routes_are_admin_only(method):
    (route,) = [r for r in _app().routes if isinstance(r, APIRoute) and r.path == SYNC_PATH and method in r.methods]
    assert _required_scopes(route.dependant) == {"admin"}


def test_the_job_is_registered_every_6_hours_and_admin_only():
    import ast
    from pathlib import Path

    from app.schedulers import scheduler
    from app.schedulers.routes.scheduler import ADMIN_ONLY_JOBS
    from app.schedulers.services.sync_sysmon_default import sync_sysmon_default

    assert scheduler.get_function_by_name("sync_sysmon_default") is sync_sysmon_default
    intervals = {}
    for node in ast.walk(ast.parse(Path(scheduler.__file__).read_text())):
        if isinstance(node, ast.Dict):
            entries = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
            if isinstance(entries.get("job_id"), ast.Constant):
                intervals[entries["job_id"].value] = entries["time_interval"].value
    assert intervals["sync_sysmon_default"] == 360
    assert "sync_sysmon_default" in ADMIN_ONLY_JOBS


def test_the_job_runs_a_check_and_never_raises(monkeypatch):
    from app.schedulers.services import sync_sysmon_default as job

    run = AsyncMock()
    monkeypatch.setattr(job, "run_sysmon_default_sync", run)
    asyncio.run(job.sync_sysmon_default())
    run.assert_awaited_once()

    monkeypatch.setattr(job, "run_sysmon_default_sync", AsyncMock(side_effect=RuntimeError("boom")))
    asyncio.run(job.sync_sysmon_default())
