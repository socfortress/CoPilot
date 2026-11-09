r"""This CoPilot's default Sysmon config, which pre-fills "Add new Configuration".

What is pinned here:
* validation can let the installer's __INSTALLDIRNAME__ placeholder through for the default, and only that: every
  other check stays, and a customer's upload and deploy keep refusing the placeholder;
* render_default_config / templatize_install_dir: the customer's code in, the placeholder back, exact and
  case-sensitive, and a round trip that gives the template back;
* the default lives in a bucket of its own (created at startup by both create_buckets), its getter tells "not set"
  from a MinIO failure, and its saver raises;
* GET/PUT /api/sysmon_config/default-config: absent, present, rendered, a read error, the placeholder restored on
  save, the audit row (no XML in it), the size limit, admin only, and routed ahead of /{customer_code}.

The configs below are small synthetic ones. The real default never belongs in this (public) repo.
No network, no database: MinIO and the audit write are fakes.

Run with: cd backend && python -m pytest tests/test_sysmon_default_config.py
"""

import asyncio
import inspect
import io
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from fastapi import UploadFile  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from miniopy_async.error import S3Error  # noqa: E402

import app.active_response.routes.sysmon_config as routes  # noqa: E402
import app.data_store.data_store_operations as store  # noqa: E402
import app.data_store.data_store_setup as store_setup  # noqa: E402
from app.active_response.schema.sysmon_config import (  # noqa: E402
    SysmonDefaultConfigSaveRequest,
)
from app.active_response.services import sysmon_config as service  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditResult  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402

PLACEHOLDER = "__INSTALLDIRNAME__"

# Shaped like the installer's template: the placeholder twice, both in install-folder paths.
TEMPLATE = r"""<Sysmon schemaversion="4.90">
  <EventFiltering>
    <RuleGroup name="" groupRelation="or">
      <ProcessCreate onmatch="exclude">
        <CommandLine condition="begin with">"C:\Program Files\__INSTALLDIRNAME__\chainsaw\chainsaw.exe"  hunt</CommandLine>
        <ParentImage condition="is">C:\Program Files\__INSTALLDIRNAME__\chainsaw\chainsaw.exe</ParentImage>
      </ProcessCreate>
    </RuleGroup>
  </EventFiltering>
</Sysmon>"""

# A config without any placeholder (e.g. one already rendered for a single customer).
PLAIN = r"""<Sysmon schemaversion="4.90">
  <EventFiltering>
    <RuleGroup name="" groupRelation="or">
      <ProcessCreate onmatch="include">
        <Image condition="end with">powershell.exe</Image>
      </ProcessCreate>
    </RuleGroup>
  </EventFiltering>
</Sysmon>"""

SKELETON = """<Sysmon schemaversion="4.60">
\t<EventFiltering>
\t\t<RuleGroup groupRelation="or"></RuleGroup>
\t</EventFiltering>
</Sysmon>"""

ADMIN = SimpleNamespace(id=1, username="admin", role_id=RoleEnum.admin.value)


def run(coroutine):
    return asyncio.run(coroutine)


def refusal(xml, **kwargs):
    with pytest.raises(HTTPException) as exc:
        run(service.validate_sysmon_config(xml, **kwargs))
    assert exc.value.status_code == 400
    return exc.value.detail


# --------------------------------------------------------------------------------------------------------------------
# Validation: the placeholder may stay in the default, nothing else changes
# --------------------------------------------------------------------------------------------------------------------


def test_the_default_may_keep_the_installer_placeholder():
    run(service.validate_sysmon_config(TEMPLATE, allow_installer_tokens=True))


def test_a_customer_config_still_may_not():
    assert PLACEHOLDER in refusal(TEMPLATE)
    assert PLACEHOLDER in refusal(TEMPLATE, allow_installer_tokens=False)


def test_the_default_still_needs_an_event_filter():
    with_placeholder = SKELETON.replace('groupRelation="or"', f'name="{PLACEHOLDER}" groupRelation="or"')
    assert "no event filters" in refusal(with_placeholder, allow_installer_tokens=True)


@pytest.mark.parametrize(
    "xml, expected",
    [
        ("<Sysmon><EventFiltering>", "Invalid XML syntax"),
        ("<NotSysmon/>", "Root element must be 'Sysmon'"),
        ("<Sysmon/>", "Missing required 'EventFiltering' element"),
        ("<Sysmon><EventFiltering/></Sysmon>", "at least one RuleGroup"),
        ("<Sysmon><EventFiltering><RuleGroup/></EventFiltering></Sysmon>", "groupRelation"),
        (f"<Sysmon><EventFiltering>{PLACEHOLDER}<RuleGroup groupRelation='or'/></EventFiltering></Sysmon>", "Invalid text content"),
    ],
)
def test_every_other_check_still_applies_to_the_default(xml, expected):
    assert expected in refusal(xml, allow_installer_tokens=True)


def test_the_upload_route_still_refuses_the_template():
    check = AsyncMock(return_value=False)
    upload = AsyncMock()
    file = UploadFile(file=io.BytesIO(TEMPLATE.encode()), filename="sysmon_config.xml")
    with patch.object(routes, "check_config_exists", check), patch.object(routes, "upload_sysmon_config", upload):
        with pytest.raises(HTTPException) as exc:
            run(routes.upload_customer_sysmon_config(customer_code="acme", file=file, session=None))
    assert exc.value.status_code == 400 and PLACEHOLDER in exc.value.detail
    upload.assert_not_awaited()


def test_a_deploy_never_reads_the_default():
    # A deploy ships the customer's stored copy, from the customers' bucket: never this CoPilot's default.
    assert store.SYSMON_CONFIG_DEFAULTS_BUCKET != "sysmon-configs"
    download = AsyncMock(return_value=b"")
    with patch.object(store, "download_data_store", download):
        run(store.download_sysmon_config("acme"))
    download.assert_awaited_once_with("sysmon-configs", "acme/sysmon_config.xml")


# --------------------------------------------------------------------------------------------------------------------
# render / templatize
# --------------------------------------------------------------------------------------------------------------------


def test_render_puts_the_customer_code_in_each_install_folder_path():
    rendered = service.render_default_config(TEMPLATE, "acme")
    assert PLACEHOLDER not in rendered
    assert rendered.count(r"C:\Program Files\acme\chainsaw\chainsaw.exe") == 2


def test_templatize_turns_the_install_folder_back_into_the_placeholder():
    content, count = service.templatize_install_dir(service.render_default_config(TEMPLATE, "acme"), "acme")
    assert (content, count) == (TEMPLATE, 2)


@pytest.mark.parametrize(
    "text",
    [
        r"C:\Program Files\acme-corp\chainsaw.exe",  # another folder that starts with the code
        r"C:\Program Files\ACME\chainsaw.exe",  # case-sensitive
        r"C:\program files\acme\chainsaw.exe",
        r"C:\Program Files (x86)\acme\chainsaw.exe",
        r"C:\Program Files\acme",  # not a folder segment: no trailing backslash
        r"C:\Users\acme\Downloads\acme.exe",  # the code anywhere else
    ],
)
def test_templatize_only_replaces_the_exact_install_folder(text):
    assert service.templatize_install_dir(text, "acme") == (text, 0)


@pytest.mark.parametrize("code", [None, "", "ac me", "ac\\me", "ac/me", "acmé", "a*", '"acme"', PLACEHOLDER])
def test_templatize_is_a_no_op_for_an_empty_or_unusual_code(code):
    rendered = TEMPLATE.replace(PLACEHOLDER, code or "")
    assert service.templatize_install_dir(rendered, code) == (rendered, 0)


@pytest.mark.parametrize("code", ["acme", "00002", "Acme_Corp", "a.b-c", "x"])
@pytest.mark.parametrize(
    "template",
    [
        TEMPLATE,
        PLAIN,
        PLAIN.replace("powershell.exe", r"C:\Program Files\__INSTALLDIRNAME__\a.exe;D:\Program Files\__INSTALLDIRNAME__\b\c.exe"),
        r"\Program Files\__INSTALLDIRNAME__\\Program Files\__INSTALLDIRNAME__\\",
    ],
)
def test_templatize_undoes_render(template, code):
    assert service.templatize_install_dir(service.render_default_config(template, code), code) == (template, template.count(PLACEHOLDER))


# --------------------------------------------------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------------------------------------------------


class _Response:
    def __init__(self, content):
        self.content = content
        self.closed = False

    async def read(self):
        return self.content

    def close(self):
        self.closed = True


class _Minio:
    """Stands in for miniopy_async.Minio: one object, or an error for get_object."""

    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []
        self.response = None
        self.session_closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.session_closed = True

    async def get_object(self, bucket_name, object_name):
        self.calls.append(("get", bucket_name, object_name))
        if self.error is not None:
            raise self.error
        self.response = _Response(self.content)
        return self.response

    async def put_object(self, bucket_name, object_name, data, length, content_type):
        self.calls.append(("put", bucket_name, object_name, data.read(), length, content_type))


def _s3_error(code):
    return S3Error(code, "stub", "/sysmon-config-defaults/sysmon_config.xml", None, None, None)


def _read(client):
    with patch.object(store, "create_session", AsyncMock(return_value=client)):
        return run(store.read_default_sysmon_config())


def test_the_default_is_read_from_its_own_bucket():
    client = _Minio(content=b"<Sysmon/>")
    assert _read(client) == b"<Sysmon/>"
    assert client.calls == [("get", "sysmon-config-defaults", "sysmon_config.xml")]
    assert client.response.closed and client.session_closed


@pytest.mark.parametrize("code", ["NoSuchKey", "NoSuchBucket"])
def test_no_object_means_no_default(code):
    assert _read(_Minio(error=_s3_error(code))) is None


@pytest.mark.parametrize(
    "error", [_s3_error("AccessDenied"), _s3_error("InternalError"), ConnectionError("MinIO is down"), OSError("timed out")]
)
def test_any_other_read_error_raises(error):
    client = _Minio(error=error)
    with pytest.raises(type(error)):
        _read(client)
    assert client.session_closed


def test_the_saver_writes_the_one_object_and_raises_on_failure():
    client = _Minio()
    bucket = AsyncMock()
    with patch.object(store, "create_session", AsyncMock(return_value=client)), patch.object(store, "create_bucket_if_not_exists", bucket):
        run(store.write_default_sysmon_config(b"<Sysmon/>"))
    bucket.assert_awaited_once_with("sysmon-config-defaults")
    assert client.calls == [("put", "sysmon-config-defaults", "sysmon_config.xml", b"<Sysmon/>", 9, "application/xml")]

    failing = _Minio()
    failing.put_object = AsyncMock(side_effect=_s3_error("AccessDenied"))
    with patch.object(store, "create_session", AsyncMock(return_value=failing)), patch.object(store, "create_bucket_if_not_exists", bucket):
        with pytest.raises(S3Error):
            run(store.write_default_sysmon_config(b"<Sysmon/>"))


@pytest.mark.parametrize("module", [store, store_setup], ids=["data_store_operations", "data_store_setup"])
def test_both_create_buckets_create_the_defaults_bucket(module):
    created = AsyncMock()
    with patch.object(module, "create_bucket_if_not_exists", created):
        run(module.create_buckets())
    assert "sysmon-config-defaults" in [call.args[0] for call in created.await_args_list]


# --------------------------------------------------------------------------------------------------------------------
# GET /api/sysmon_config/default-config
# --------------------------------------------------------------------------------------------------------------------


def _get(stored, customer_code=None):
    read = AsyncMock(side_effect=stored) if isinstance(stored, BaseException) else AsyncMock(return_value=stored)
    with patch.object(routes, "read_default_sysmon_config", read):
        return run(routes.get_sysmon_default_config(customer_code=customer_code))


def test_no_default_set_is_not_an_error():
    result = _get(None, "acme")
    assert result.success is True and result.present is False
    assert result.config_content is None and result.rendered_for is None
    assert "No default Sysmon config is set on this CoPilot" in result.message


def test_the_default_comes_back_as_stored_without_a_customer_code():
    result = _get(TEMPLATE.encode())
    assert result.present is True and result.config_content == TEMPLATE and result.rendered_for is None


def test_the_default_comes_back_rendered_for_a_customer():
    result = _get(TEMPLATE.encode(), "acme")
    assert result.present is True and result.rendered_for == "acme"
    assert result.config_content == service.render_default_config(TEMPLATE, "acme")
    assert PLACEHOLDER not in result.config_content


@pytest.mark.parametrize("error", [ConnectionError("MinIO is down"), _s3_error("AccessDenied")])
def test_a_read_error_is_a_server_error_not_an_absent_default(error):
    with pytest.raises(HTTPException) as exc:
        _get(error, "acme")
    assert exc.value.status_code >= 500
    assert "Could not read this CoPilot's default Sysmon config" in exc.value.detail


def test_a_default_that_is_not_utf8_is_a_server_error():
    with pytest.raises(HTTPException) as exc:
        _get(b"\xff\xfe<\x00S\x00")
    assert exc.value.status_code == 500 and "not valid UTF-8" in exc.value.detail


# --------------------------------------------------------------------------------------------------------------------
# PUT /api/sysmon_config/default-config
# --------------------------------------------------------------------------------------------------------------------


def _put(config_content, customer_code=None, write=None):
    write = write or AsyncMock()
    upload = AsyncMock()
    body = SysmonDefaultConfigSaveRequest(config_content=config_content, customer_code=customer_code)
    with patch.object(routes, "write_default_sysmon_config", write), patch.object(routes, "upload_sysmon_config", upload):
        try:
            return run(routes.save_sysmon_default_config(body, request=None, current_user=ADMIN)), write
        finally:
            # Saving the default never touches a customer's stored config.
            upload.assert_not_awaited()


def _default_rows(audit_rows):
    return [row for row in audit_rows if row.action == AuditAction.SYSMON_CONFIG_DEFAULT_SAVE.value]


def test_the_customer_install_folder_is_turned_back_into_the_placeholder_on_save(audit_rows):
    result, write = _put(service.render_default_config(TEMPLATE, "acme"), "acme")
    write.assert_awaited_once_with(TEMPLATE.encode())
    assert result.success and (result.placeholders, result.restored) == (2, 2)
    assert '2 of them turned back from "acme"' in result.message


def test_a_template_saved_as_is_keeps_its_placeholders(audit_rows):
    result, write = _put(TEMPLATE)
    write.assert_awaited_once_with(TEMPLATE.encode())
    assert (result.placeholders, result.restored) == (2, 0)


def test_a_default_without_placeholders_says_every_new_config_gets_the_same_paths(audit_rows):
    result, write = _put(PLAIN, "acme")
    write.assert_awaited_once_with(PLAIN.encode())
    assert (result.placeholders, result.restored) == (0, 0)
    assert "every new configuration will get these exact install-folder paths" in result.message


def test_the_audit_row_identifies_the_config_without_holding_it(audit_rows):
    import hashlib

    _put(service.render_default_config(TEMPLATE, "acme"), "acme")
    (row,) = _default_rows(audit_rows)
    assert row.action == "response.sysmon_default_save"
    assert row.result == AuditResult.SUCCESS.value
    assert (row.actor_user_id, row.actor_username, row.customer_code) == (1, "admin", None)
    assert row.new_value == {
        "sha256": hashlib.sha256(TEMPLATE.encode()).hexdigest(),
        "size": len(TEMPLATE.encode()),
        "placeholders": 2,
        "restored": 2,
        "customer_code": "acme",
    }
    stored = json.dumps(row.model_dump(), default=str)
    assert "chainsaw" not in stored and "<Sysmon" not in stored and "EventFiltering" not in stored


def test_a_config_over_5_mib_is_refused_before_anything_is_saved(audit_rows):
    padding = "<!-- " + "x" * (5 * 1024 * 1024) + " -->"
    with pytest.raises(HTTPException) as exc:
        _put(TEMPLATE.replace("<EventFiltering>", padding + "<EventFiltering>"))
    assert exc.value.status_code == 413 and "5 MiB" in exc.value.detail
    assert _default_rows(audit_rows) == []


def test_exactly_5_mib_is_accepted(audit_rows):
    filler = 5 * 1024 * 1024 - len(TEMPLATE.encode()) - len("<!--  -->")
    content = TEMPLATE.replace("<EventFiltering>", "<!-- " + "x" * filler + " --><EventFiltering>")
    assert len(content.encode()) == 5 * 1024 * 1024
    result, write = _put(content)
    assert result.success and write.await_count == 1


@pytest.mark.parametrize("content, reason", [(SKELETON, "no event filters"), ("<Sysmon><EventFiltering>", "Invalid XML syntax")])
def test_an_invalid_default_is_refused_and_not_saved(audit_rows, content, reason):
    write = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        _put(content, "acme", write)
    assert exc.value.status_code == 400 and reason in exc.value.detail
    write.assert_not_awaited()
    assert _default_rows(audit_rows) == []


def test_a_failed_save_is_a_server_error_and_audited_as_a_failure(audit_rows):
    with pytest.raises(HTTPException) as exc:
        _put(TEMPLATE, write=AsyncMock(side_effect=ConnectionError("MinIO is down")))
    assert exc.value.status_code >= 500 and "Could not save this CoPilot's default Sysmon config" in exc.value.detail
    (row,) = _default_rows(audit_rows)
    assert row.result == AuditResult.FAILURE.value and "MinIO is down" in row.details
    assert "chainsaw" not in json.dumps(row.model_dump(), default=str)


# --------------------------------------------------------------------------------------------------------------------
# Routing and access
# --------------------------------------------------------------------------------------------------------------------

DEFAULT_PATH = "/api/sysmon_config/default-config"


def _app():
    import copilot

    return copilot.app


def _resolve(method, path):
    """The endpoint the app's router picks for a request, the way Starlette does: the first full match wins."""
    from starlette.routing import Match

    scope = {"type": "http", "method": method, "path": path, "root_path": "", "query_string": b"", "headers": []}
    for route in _app().router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "endpoint", None)
    return None


def test_the_default_config_path_is_not_taken_for_a_customer_code():
    assert _resolve("GET", DEFAULT_PATH) is routes.get_sysmon_default_config
    assert _resolve("PUT", DEFAULT_PATH) is routes.save_sysmon_default_config
    # A customer's download is still reachable.
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


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_the_default_config_is_admin_only(method):
    (route,) = [r for r in _app().routes if isinstance(r, APIRoute) and r.path == DEFAULT_PATH and method in r.methods]
    assert _required_scopes(route.dependant) == {"admin"}
