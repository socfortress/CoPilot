"""
Phase 0 Sysmon sensor health for Windows_<code> agent groups.

Three things have to reach a customer's Windows group, in this order, for the Sysmon watchdog and the fixed daily
config reload to work. Pushing them in another order loses the watchdog's first results, and the watchdog's one-time
``sc.exe`` calls alert at level 13 instead of being relabelled:

1. ``sysmon_sensor_health_rules.xml`` in the manager's ``etc/rules``. It is per manager, not per customer, and loading
   it restarts the manager (the whole cluster when clustered), so CoPilot only installs it when explicitly asked to.
2. ``sysmon_watchdog.ps1`` and ``sysmon_config_reload.ps1`` in the group's shared folder. The Wazuh API cannot upload
   arbitrary shared files, so they go through the WAZUH-UTILS sidecar on the master. These scripts run as SYSTEM on
   every endpoint of the group, so CoPilot only sends them to an authenticated sidecar, over https: both
   ``WAZUH_UTILS_API_KEY`` and an https ``WAZUH_UTILS_URL`` must be set. The sidecar's (self-signed) certificate is
   only verified when ``WAZUH_UTILS_CA_BUNDLE`` is set.
3. The two ``<wodle name="command">`` blocks in the group's agent.conf: ``sysmon-watchdog`` and ``sysmon-reload``.
   The canonical text is the ``SYSMON-HEALTH`` block at the end of ``customer_provisioning/templates/windows_agent.conf``,
   so new groups (provisioning) and existing groups (the admin backfill) get the same thing. A wodle is only written
   when its prerequisites are in place; the reload also needs a deployed ``sysmon_config.xml``.

Reads are three-way (present / missing / could not read): a wodle is never added or removed on the strength of a read
that failed. The Wazuh API re-indents agent.conf when it stores it, so agent.conf is compared ignoring indentation.

The scripts and the rules file are vendored byte-exact under ``app/active_response/assets/sysmon_health`` and checked
against ``manifest.json`` before every use. The source of truth is socfortress/Client-Kickstart-Automated
(``wazuh/``); the rules file also ships with socfortress/Wazuh-Rules.
"""
import asyncio
import difflib
import hashlib
import ipaddress
import json
import os
import re
import ssl
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union
from urllib.parse import quote
from urllib.parse import urlparse

import aiohttp
import requests
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.active_response.schema.sysmon_health import SysmonHealthApplyAllResult
from app.active_response.schema.sysmon_health import SysmonHealthApplyResult
from app.active_response.schema.sysmon_health import SysmonHealthFileState
from app.active_response.schema.sysmon_health import SysmonHealthStatus
from app.active_response.schema.sysmon_health import SysmonHealthStep
from app.blocking import run_blocking
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_manager.utils.universal import WAZUH_REQUEST_TIMEOUT
from app.connectors.wazuh_manager.utils.universal import create_wazuh_manager_client
from app.connectors.wazuh_manager.utils.universal import get_cluster_status
from app.connectors.wazuh_manager.utils.universal import invalidate_wazuh_token_cache
from app.connectors.wazuh_manager.utils.universal import restart_wazuh_manager_service
from app.connectors.wazuh_manager.utils.universal import send_delete_request
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.db.db_session import AsyncSessionLocal
from app.db.universal_models import CustomersMeta

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "sysmon_health"
WINDOWS_TEMPLATE = Path(__file__).resolve().parents[2] / "customer_provisioning" / "templates" / "windows_agent.conf"

RULES_FILENAME = "sysmon_sensor_health_rules.xml"
RULES_DIRNAME = "etc/rules"
WATCHDOG_SCRIPT = "sysmon_watchdog.ps1"
RELOAD_SCRIPT = "sysmon_config_reload.ps1"
SHARED_SCRIPTS = (WATCHDOG_SCRIPT, RELOAD_SCRIPT)
SYSMON_CONFIG = "sysmon_config.xml"

WATCHDOG_TAG = "sysmon-watchdog"
RELOAD_TAG = "sysmon-reload"
MANAGED_TAGS = (WATCHDOG_TAG, RELOAD_TAG)

BLOCK_BEGIN = "<!-- BEGIN SYSMON-HEALTH"
BLOCK_END = "<!-- END SYSMON-HEALTH -->"

# Wazuh group names: letters, digits, '_', '-', '.'. Anything else is refused before it reaches a URL path.
GROUP_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,255}$")
# Wazuh API error codes meaning "no such file / group" (anything else is a read failure, not an absence).
MISSING_CODES = {1006, 1415, 1710}

# One rollout at a time: the rules install restarts the manager, and agent.conf writes are read-modify-write.
SYSMON_HEALTH_LOCK = asyncio.Lock()

RESTART_WAIT_SECONDS = 240
SYNC_WAIT_SECONDS = 120
POLL_SECONDS = 10


class SysmonHealthAssetError(RuntimeError):
    """A vendored asset is missing or does not match manifest.json; nothing is published."""


# --------------------------------------------------------------------------------------------------------------------
# Vendored assets
# --------------------------------------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _manifest() -> Dict[str, object]:
    return json.loads((ASSET_DIR / "manifest.json").read_text())


def asset_sha256(name: str) -> str:
    try:
        return str(_manifest()["files"][name])
    except KeyError as e:
        raise SysmonHealthAssetError(f"{name} is not listed in {ASSET_DIR / 'manifest.json'}") from e


def asset_version() -> Dict[str, object]:
    """What CoPilot ships, for audit rows: the source commit and each file's sha256."""
    manifest = _manifest()
    return {"source_commit": manifest.get("source_commit"), "files": dict(manifest.get("files", {}))}


def load_asset(name: str) -> bytes:
    """The vendored file, read as bytes (the reload script carries a UTF-8 BOM that must survive), hash-checked."""
    expected = asset_sha256(name)
    try:
        content = (ASSET_DIR / name).read_bytes()
    except OSError as e:
        raise SysmonHealthAssetError(f"Cannot read vendored asset {name}: {e}") from e
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        raise SysmonHealthAssetError(f"Vendored asset {name} has sha256 {actual}, manifest.json expects {expected}")
    return content


def expected_rule_count() -> int:
    return len(re.findall(rb"<rule\s+id=", load_asset(RULES_FILENAME)))


# --------------------------------------------------------------------------------------------------------------------
# agent.conf text handling (pure functions; the file is edited as text so everything else stays as it is)
# --------------------------------------------------------------------------------------------------------------------

_WODLE_RE = re.compile(r"<wodle\b[^>]*\bname\s*=\s*([\"'])command\1[^>]*>.*?</wodle\s*>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<tag>\s*([^<]+?)\s*</tag>", re.IGNORECASE)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def managed_block(template_text: Optional[str] = None) -> str:
    """The canonical SYSMON-HEALTH block (from BEGIN marker to END marker plus newline) of the Windows template."""
    text = template_text if template_text is not None else WINDOWS_TEMPLATE.read_text()
    start = text.find(BLOCK_BEGIN)
    end = text.find(BLOCK_END)
    if start < 0 or end < 0 or end < start:
        raise SysmonHealthAssetError(f"The SYSMON-HEALTH block is missing from {WINDOWS_TEMPLATE}")
    return text[start : end + len(BLOCK_END)] + "\n"


def _mask_comments(text: str) -> str:
    """``text`` with every comment blanked out character for character, so offsets still match the original."""
    return _COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def tagged_wodles(text: str, tags: Iterable[str] = MANAGED_TAGS) -> List[Tuple[int, int, str]]:
    """``(start, end, tag)`` of every active (not commented-out) command wodle whose <tag> is one of ``tags``."""
    wanted = set(tags)
    masked = _mask_comments(text)
    found = []
    for match in _WODLE_RE.finditer(masked):
        tag_match = _TAG_RE.search(match.group(0))
        if tag_match and tag_match.group(1) in wanted:
            found.append((match.start(), match.end(), tag_match.group(1)))
    return found


def wodle_tags_present(text: str) -> List[str]:
    return sorted({tag for _, _, tag in tagged_wodles(text)})


def _cut(text: str, start: int, end: int) -> str:
    """Remove text[start:end] together with the indentation before it and the line break after it."""
    line_start = text.rfind("\n", 0, start) + 1
    if text[line_start:start].strip() == "":
        start = line_start
    if text.startswith("\r\n", end):
        end += 2
    elif text.startswith("\n", end):
        end += 1
    return text[:start] + text[end:]


def strip_managed(text: str) -> str:
    """agent.conf without the SYSMON-HEALTH block and without any other sysmon-watchdog / sysmon-reload wodle."""
    begin = text.find(BLOCK_BEGIN)
    if begin >= 0:
        end = text.find(BLOCK_END, begin)
        if end < 0:
            raise ValueError("agent.conf has a SYSMON-HEALTH begin marker without its end marker; fix it by hand first")
        text = _cut(text, begin, end + len(BLOCK_END))
    for start, end, _tag in sorted(tagged_wodles(text), reverse=True):
        text = _cut(text, start, end)
    return text


def build_block(wanted: Iterable[str], template_text: Optional[str] = None) -> str:
    """The managed block keeping only the wodles in ``wanted``; an empty string when none is wanted."""
    wanted = set(wanted)
    block = managed_block(template_text)
    if not wanted & set(MANAGED_TAGS):
        return ""
    for start, end, tag in sorted(tagged_wodles(block), reverse=True):
        if tag not in wanted:
            block = _cut(block, start, end)
    return block


def reconcile_agent_conf(current: str, wanted: Iterable[str], template_text: Optional[str] = None) -> str:
    """
    ``current`` with the managed wodles replaced by the canonical block holding ``wanted``.

    Hand-added sysmon-watchdog / sysmon-reload wodles anywhere in the file are removed, so there is never more than
    one of each; the block goes at the end as its own ``<agent_config os="Windows">``. Idempotent.
    """
    base = strip_managed(current)
    block = build_block(wanted, template_text)
    if not block:
        return base if base.endswith("\n") else base + "\n"
    return base.rstrip("\r\n") + "\n" + block


def normalized(text: Optional[str]) -> Optional[List[str]]:
    """agent.conf compared the way the Wazuh API stores it: it re-indents on write (minidom) and drops blank lines."""
    if text is None:
        return None
    return [line.strip() for line in text.splitlines() if line.strip()]


def same_agent_conf(a: Optional[str], b: Optional[str]) -> bool:
    return a is not None and b is not None and normalized(a) == normalized(b)


def unified_diff(before: str, after: str, name: str = "agent.conf") -> Optional[str]:
    if same_agent_conf(before, after):
        return None
    return "".join(
        difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), f"{name} (current)", f"{name} (new)"),
    )


# --------------------------------------------------------------------------------------------------------------------
# Manager reads (three-way)
# --------------------------------------------------------------------------------------------------------------------


@dataclass
class RawFile:
    """A raw read from the Wazuh API: ``ok`` (content holds the exact bytes), ``missing``, or ``error``."""

    state: str
    content: Optional[bytes] = None
    detail: str = ""


def windows_group(customer_meta_wazuh_group: str) -> str:
    return f"Windows_{customer_meta_wazuh_group}"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _envelope_codes(body: bytes) -> Tuple[Optional[int], Set[int]]:
    """``(error, {failed item codes})`` of a Wazuh JSON envelope; ``(None, set())`` when the body is not one."""
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, set()
    if not isinstance(data, dict):
        return None, set()
    codes = set()
    if isinstance(data.get("code"), int):
        codes.add(data["code"])
    failed = (data.get("data") or {}).get("failed_items") if isinstance(data.get("data"), dict) else None
    for item in failed or []:
        code = ((item or {}).get("error") or {}).get("code")
        if isinstance(code, int):
            codes.add(code)
    error = data.get("error")
    return (error if isinstance(error, int) else None), codes


async def _get_raw(endpoint: str, params: Optional[dict] = None, connector_name: str = "Wazuh-Manager") -> RawFile:
    """
    Exact file bytes from the Wazuh API (``raw=true``).

    Not ``send_get_request``: that returns ``response.text``, which requests decodes with a guessed charset, mangling
    the reload script's UTF-8 BOM. And the Wazuh API answers some missing files with HTTP 200 and a JSON error
    envelope (rules files, code 1415), which must not be mistaken for the file.
    """
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if not attributes or not attributes.get("connector_url"):
        return RawFile("error", detail="no Wazuh-Manager connector")
    query = {"raw": "true"}
    query.update(params or {})
    for attempt in (1, 2):
        headers = await create_wazuh_manager_client(connector_name)
        if not headers:
            return RawFile("error", detail="cannot authenticate to the Wazuh API")
        try:
            response = await run_blocking(
                requests.get,
                f"{attributes['connector_url']}{endpoint}",
                headers=dict(headers),
                params=query,
                verify=False,
                timeout=WAZUH_REQUEST_TIMEOUT,
            )
        except Exception as e:  # noqa: BLE001 - reported as a read failure, never as an absence
            return RawFile("error", detail=f"request failed: {e}")
        if response.status_code == 401 and attempt == 1:
            await invalidate_wazuh_token_cache(connector_name)
            continue
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and not content_type.startswith("application/json"):
            return RawFile("ok", content=response.content)
        error, codes = _envelope_codes(response.content)
        if codes & MISSING_CODES:
            return RawFile("missing")
        if response.status_code == 200 and error == 0:
            return RawFile("ok", content=response.content)
        return RawFile("error", detail=f"HTTP {response.status_code}, Wazuh error codes {sorted(codes) or error}")
    return RawFile("error", detail="authentication failed twice")


def _file_state(name: str, read: RawFile) -> SysmonHealthFileState:
    expected = asset_sha256(name)
    if read.state == "ok":
        actual = _sha256(read.content)
        return SysmonHealthFileState(name=name, present=True, current=actual == expected, sha256=actual, expected_sha256=expected)
    return SysmonHealthFileState(name=name, readable=read.state == "missing", read_error=read.detail or None, expected_sha256=expected)


async def _group_exists(group: str) -> Optional[bool]:
    """True / False, or None when the manager could not be asked."""
    response = await send_get_request(endpoint="/groups", params={"groups_list": group})
    if not response or not response.get("success"):
        return None
    items = ((response.get("data") or {}).get("data") or {}).get("affected_items") or []
    return any(item.get("name") == group for item in items)


async def rules_state() -> SysmonHealthFileState:
    return _file_state(RULES_FILENAME, await _get_raw(f"/rules/files/{RULES_FILENAME}", {"relative_dirname": RULES_DIRNAME}))


async def shared_script_states(group: str) -> List[SysmonHealthFileState]:
    quoted = quote(group, safe="")
    return [_file_state(name, await _get_raw(f"/groups/{quoted}/files/{name}")) for name in SHARED_SCRIPTS]


async def _sysmon_config_read(group: str) -> RawFile:
    read = await _get_raw(f"/groups/{quote(group, safe='')}/files/{SYSMON_CONFIG}")
    return RawFile(read.state, detail=read.detail)  # only existence matters; don't keep 400 KB around


async def _get_agent_conf(group: str) -> Optional[str]:
    read = await _get_raw(f"/groups/{quote(group, safe='')}/files/agent.conf")
    return read.content.decode("utf-8") if read.state == "ok" else None


def wanted_wodles(rules_ok: bool, scripts: Dict[str, bool], sysmon_config_present: bool) -> Set[str]:
    """Which managed wodles may be written: each one only when everything it depends on is in place."""
    wanted = set()
    if rules_ok and scripts.get(WATCHDOG_SCRIPT):
        wanted.add(WATCHDOG_TAG)
    if rules_ok and scripts.get(RELOAD_SCRIPT) and sysmon_config_present:
        wanted.add(RELOAD_TAG)
    return wanted


async def get_customer_wazuh_group(customer_code: str, session: AsyncSession) -> Optional[str]:
    result = await session.execute(select(CustomersMeta).where(CustomersMeta.customer_code == customer_code))
    meta = result.scalars().first()
    return meta.customer_meta_wazuh_group if meta and meta.customer_meta_wazuh_group else None


async def get_sysmon_health_status(customer_code: str, session: AsyncSession) -> SysmonHealthStatus:
    wazuh_group = await get_customer_wazuh_group(customer_code, session)
    group = windows_group(wazuh_group or customer_code)
    status = SysmonHealthStatus(customer_code=customer_code, group=group)
    if not wazuh_group:
        status.problems.append("No customer meta (Wazuh group) is recorded for this customer; assuming the group is named after the code.")
    if not GROUP_NAME_RE.match(group):
        status.problems.append(f"{group!r} is not a valid Wazuh group name.")
        status.message = "Invalid group name."
        return status

    exists = await _group_exists(group)
    status.group_exists = bool(exists)
    status.rules = await rules_state()
    if exists is None:
        status.read_errors.append("Could not ask the manager whether the group exists.")
        status.message = "The manager could not be read."
        return status
    if not exists:
        status.problems.append(f"Wazuh group {group} does not exist on the manager.")
        status.message = "Group not found."
        return status

    status.shared_files = await shared_script_states(group)
    config_read = await _sysmon_config_read(group)
    status.sysmon_config_present = config_read.state == "ok"
    agent_conf = await _get_agent_conf(group)

    for state in [status.rules] + status.shared_files:
        if not state.readable:
            status.read_errors.append(f"Could not read {state.name}: {state.read_error}")
    if config_read.state == "error":
        status.read_errors.append(f"Could not read {SYSMON_CONFIG}: {config_read.detail}")
    if agent_conf is None:
        status.read_errors.append("Could not read the group's agent.conf.")

    scripts_ok = {state.name: state.current for state in status.shared_files}
    status.wodles_wanted = sorted(wanted_wodles(status.rules.current, scripts_ok, status.sysmon_config_present))
    if agent_conf is not None:
        status.wodles_present = wodle_tags_present(agent_conf)
        try:
            status.agent_conf_current = same_agent_conf(reconcile_agent_conf(agent_conf, status.wodles_wanted), agent_conf)
        except ValueError as e:
            status.problems.append(str(e))

    if status.rules.readable and not status.rules.current:
        status.problems.append(
            f"{RULES_FILENAME} is {'outdated' if status.rules.present else 'missing'} on the manager (install it with install_rules=true; this restarts the manager).",
        )
    for state in status.shared_files:
        if state.readable and not state.current:
            status.problems.append(f"{state.name} is {'outdated' if state.present else 'missing'} in the group's shared folder.")
    if config_read.state == "missing":
        status.problems.append("No sysmon_config.xml is deployed to this group yet, so the sysmon-reload wodle is held back.")
    if agent_conf is not None and not status.agent_conf_current and not status.read_errors:
        status.problems.append("agent.conf does not match the managed wodles yet.")
    if status.read_errors:
        status.message = f"{len(status.read_errors)} item(s) could not be read; nothing should be changed until they can."
    else:
        status.message = "Up to date." if not status.problems else f"{len(status.problems)} item(s) need attention."
    return status


# --------------------------------------------------------------------------------------------------------------------
# Manager writes
# --------------------------------------------------------------------------------------------------------------------


def _wazuh_ok(response: Optional[dict]) -> bool:
    if not response or not response.get("success"):
        return False
    data = response.get("data") or {}
    if isinstance(data, dict) and data.get("error") not in (None, 0):
        return False
    return True


def _wazuh_message(response: Optional[dict]) -> str:
    if not response:
        return "no response"
    data = response.get("data") or {}
    if isinstance(data, dict) and data.get("message"):
        return str(data.get("message"))
    return str(response.get("message", "unknown error"))


async def _cluster_enabled() -> Optional[bool]:
    cluster = await get_cluster_status()
    if not cluster or not cluster.get("success"):
        return None
    return ((cluster.get("data") or {}).get("data") or {}).get("enabled") == "yes"


async def validate_manager_configuration() -> Tuple[Optional[bool], str]:
    """
    ``(True, "")`` when the manager (every node, when clustered) accepts its configuration and ruleset,
    ``(False, why)`` when it reports it invalid, ``(None, why)`` when the check itself could not run.
    """
    enabled = await _cluster_enabled()
    endpoint = "/cluster/configuration/validation" if enabled else "/manager/configuration/validation"
    # wait_for_complete: `-t` of every daemon can exceed the API's own 10 s request timeout on a big ruleset.
    response = await send_get_request(endpoint=endpoint, params={"wait_for_complete": "true"})
    if not response or not response.get("success"):
        return None, f"the validation request failed ({(response or {}).get('message', 'no response')})"
    data = (response.get("data") or {}).get("data") or {}
    if data.get("total_failed_items", 0) or data.get("failed_items"):
        return False, f"invalid: {data.get('failed_items')}"
    statuses = {item.get("status") for item in data.get("affected_items", [])}
    if statuses and statuses != {"OK"}:
        return False, f"invalid: {data.get('affected_items')}"
    return True, ""


async def _upload_rules(content: bytes) -> Optional[dict]:
    return await send_put_request(
        endpoint=f"/rules/files/{RULES_FILENAME}",
        data=content,
        params={"overwrite": "true", "relative_dirname": RULES_DIRNAME},
        binary_data=True,
    )


async def _rollback_rules(previous: RawFile) -> Tuple[bool, str]:
    """Put the previous rules file back (or remove ours when there was none) and say whether that worked."""
    if previous.state == "ok":
        response = await _upload_rules(previous.content)
        action = "restored the previous file"
    else:
        response = await send_delete_request(endpoint=f"/rules/files/{RULES_FILENAME}", params={"relative_dirname": RULES_DIRNAME})
        action = "removed the new file"
    if _wazuh_ok(response):
        return True, action
    return False, (
        f"could NOT roll back ({_wazuh_message(response)}): the new {RULES_FILENAME} is still on disk unvalidated. "
        "Do not restart the manager until it is fixed or removed by hand"
    )


async def _analysisd_uptimes() -> Optional[Dict[str, str]]:
    """``{node: analysisd start time}`` for every node (just the manager when not clustered), or None if unreadable."""
    enabled = await _cluster_enabled()
    nodes: List[str] = []
    if enabled:
        listing = await send_get_request(endpoint="/cluster/nodes")
        if not listing or not listing.get("success"):
            return None
        items = ((listing.get("data") or {}).get("data") or {}).get("affected_items", [])
        nodes = [item.get("name") for item in items if item.get("name")]
    uptimes = {}
    for node in nodes or [None]:
        endpoint = f"/cluster/{quote(node, safe='')}/daemons/stats" if node else "/manager/daemons/stats"
        response = await send_get_request(endpoint=endpoint, params={"daemons_list": "wazuh-analysisd"})
        if not response or not response.get("success"):
            return None
        items = ((response.get("data") or {}).get("data") or {}).get("affected_items") or []
        if not items or not items[0].get("uptime"):
            return None
        uptimes[node or "manager"] = str(items[0]["uptime"])
    return uptimes


async def _wait_for_ruleset_sync(sleep) -> bool:
    """Clustered: wait until every worker has the uploaded file, so no node restarts without it."""
    waited = 0
    while waited <= SYNC_WAIT_SECONDS:
        response = await send_get_request(endpoint="/cluster/ruleset/synchronization")
        items = (((response or {}).get("data") or {}).get("data") or {}).get("affected_items") or []
        if response and response.get("success") and items and all(item.get("synced") for item in items):
            return True
        await sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    return False


async def install_rules(sleep=asyncio.sleep) -> SysmonHealthStep:
    """
    Upload the rules file, validate, restart the manager, and confirm every node's analysisd restarted on it.

    Guarded: any failure before the restart rolls the file back (verified) and does not restart. After a confirmed
    restart, "the current file is on disk" therefore also means "it is loaded".
    """
    content = load_asset(RULES_FILENAME)
    previous = await _get_raw(f"/rules/files/{RULES_FILENAME}", {"relative_dirname": RULES_DIRNAME})
    if previous.state == "error":
        return SysmonHealthStep(
            name="rules",
            status="failed",
            detail=f"Could not read the current rules file ({previous.detail}); nothing was changed.",
        )
    before = await _analysisd_uptimes()
    if before is None:
        return SysmonHealthStep(
            name="rules",
            status="failed",
            detail="Could not read analysisd's start time to confirm a restart later; nothing was changed.",
        )

    response = await _upload_rules(content)
    if not _wazuh_ok(response):
        return SysmonHealthStep(name="rules", status="failed", detail=f"The manager refused the rules file: {_wazuh_message(response)}")

    if await _cluster_enabled() and not await _wait_for_ruleset_sync(sleep):
        _, how = await _rollback_rules(previous)
        return SysmonHealthStep(
            name="rules",
            status="failed",
            detail=f"The workers did not receive the file within {SYNC_WAIT_SECONDS}s; {how}.",
        )

    valid, why = await validate_manager_configuration()
    if not valid:
        _, how = await _rollback_rules(previous)
        kind = "did not validate" if valid is False else "could not be validated"
        return SysmonHealthStep(
            name="rules",
            status="failed",
            detail=f"The new ruleset {kind} ({why}); {how}; the manager was not restarted.",
        )

    restart = await restart_wazuh_manager_service()
    if not restart or not restart.get("success"):
        _, how = await _rollback_rules(previous)
        return SysmonHealthStep(
            name="rules",
            status="failed",
            detail=f"The restart request failed ({(restart or {}).get('message', 'no response')}); {how}.",
        )

    waited = 0
    after = None
    while waited <= RESTART_WAIT_SECONDS:
        await sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        after = await _analysisd_uptimes()
        if after and set(after) == set(before) and all(after[node] != before[node] for node in before):
            return SysmonHealthStep(name="rules", status="changed", detail=f"Installed; analysisd restarted on {', '.join(sorted(after))}.")
    return SysmonHealthStep(
        name="rules",
        status="failed",
        detail=(
            f"The restart was requested but analysisd did not report a new start time on every node within {RESTART_WAIT_SECONDS}s "
            f"(before {before}, after {after}). The new file is on disk; check the manager before applying to groups."
        ),
    )


# aiohttp's ssl= argument: False (encrypted, certificate not verified), an SSLContext (verified), or None (http).
SidecarSSL = Union[ssl.SSLContext, bool, None]


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def sidecar_settings(path: str = "/provision_worker/shared-files") -> Tuple[Optional[str], Optional[str], SidecarSSL]:
    """
    ``(endpoint, refusal, ssl)`` for the authenticated WAZUH-UTILS: refuses unless WAZUH_UTILS_API_KEY and an https (or
    loopback, or explicitly allowed http) WAZUH_UTILS_URL are configured. Also used by the Sysmon config deploy once a
    key is set.

    ``ssl`` is passed straight to aiohttp. Over https the sidecar's certificate is not verified unless
    WAZUH_UTILS_CA_BUNDLE is set (``False``), the same way CoPilot already talks to the Wazuh API: the connection is
    still encrypted and the API key is what authenticates. With WAZUH_UTILS_CA_BUNDLE the certificate is verified
    against that file (an SSLContext). Over http it is ``None``.
    """
    token = os.environ.get("WAZUH_UTILS_API_KEY", "").strip()
    base = os.environ.get("WAZUH_UTILS_URL", "").strip().rstrip("/")
    if not token:
        refusal = (
            "WAZUH_UTILS_API_KEY is not set. These scripts run as SYSTEM on every endpoint, so CoPilot only sends them "
            "to an authenticated WAZUH-UTILS; upgrade the sidecar on the master and set the key."
        )
        return None, refusal, None
    if not base:
        return None, "WAZUH_UTILS_URL is not set: give the authenticated WAZUH-UTILS address explicitly, e.g. https://<master>:5003.", None
    parsed = urlparse(base)
    insecure_ok = os.environ.get("WAZUH_UTILS_ALLOW_INSECURE_HTTP", "").strip().lower() in ("1", "true", "yes")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and (_is_loopback(parsed.hostname or "") or insecure_ok)):
        refusal = (
            f"Refusing to send the API key to {base}: use https (set WAZUH_UTILS_ALLOW_INSECURE_HTTP=true "
            "only if you accept it crossing the network in cleartext)."
        )
        return None, refusal, None
    context: SidecarSSL = None
    if parsed.scheme == "https":
        ca_bundle = os.environ.get("WAZUH_UTILS_CA_BUNDLE", "").strip()
        context = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else False
    return f"{base}{path}", None, context


def _sidecar_settings() -> Tuple[Optional[str], Optional[str], SidecarSSL]:
    return sidecar_settings("/provision_worker/shared-files")


async def publish_shared_scripts(group: str, names: Iterable[str] = SHARED_SCRIPTS) -> Tuple[bool, str]:
    """
    Send the vendored scripts to the WAZUH-UTILS sidecar, which writes them into /var/ossec/etc/shared/<group>/.

    Contract (WAZUH-UTILS, authenticated build): ``POST /provision_worker/shared-files``, ``Authorization: Bearer
    <WAZUH_UTILS_API_KEY>``, multipart ``group`` plus, per script, one ``files`` part and one ``sha256`` field (in the
    same order). The sidecar verifies each hash before writing, only accepts allow-listed file names for an existing
    Windows_* group, and writes atomically as wazuh:wazuh 0660.
    """
    if not GROUP_NAME_RE.match(group):
        return False, f"{group!r} is not a valid Wazuh group name."
    try:
        endpoint, refusal, context = _sidecar_settings()
    except (OSError, ssl.SSLError) as e:
        return False, f"Cannot load WAZUH_UTILS_CA_BUNDLE: {e}"
    if refusal:
        return False, refusal
    token = os.environ.get("WAZUH_UTILS_API_KEY", "").strip()

    form = aiohttp.FormData()
    form.add_field("group", group)
    for name in names:
        form.add_field("files", load_asset(name), filename=name, content_type="application/octet-stream")
        form.add_field("sha256", asset_sha256(name))
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as http_session:
            async with http_session.post(endpoint, data=form, headers={"Authorization": f"Bearer {token}"}, ssl=context) as response:
                body = await response.text()
                if response.status == 200:
                    return True, "Published to the shared folder."
                try:
                    payload = json.loads(body)
                except ValueError:
                    payload = {}
                # The authenticated sidecar answers {"success": false, "message": ...}; a route that does not exist
                # (an older sidecar) answers FastAPI's default {"detail": "Not Found"}.
                message = payload.get("message") if isinstance(payload, dict) else None
                if response.status == 404 and not message:
                    return False, "WAZUH-UTILS on the master has no /shared-files endpoint yet; upgrade it."
                if response.status == 401:
                    return False, "WAZUH-UTILS rejected the API key (HTTP 401)."
                return False, f"WAZUH-UTILS refused (HTTP {response.status}): {message or body[:300]}"
    except Exception as e:  # noqa: BLE001 - network failures are reported, not raised
        return False, f"Could not reach WAZUH-UTILS at {endpoint}: {e}"


async def _put_agent_conf(group: str, content: str) -> Optional[dict]:
    return await send_put_request(endpoint=f"/groups/{quote(group, safe='')}/configuration", data=content.encode("utf-8"), xml_data=True)


# --------------------------------------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------------------------------------


async def _apply_unlocked(result: SysmonHealthApplyResult, session: AsyncSession, install_rules_if_needed: bool) -> SysmonHealthApplyResult:
    dry_run = result.dry_run
    status = await get_sysmon_health_status(result.customer_code, session)
    result.group, result.status = status.group, status

    def stop(name: str, step_status: str, detail: str, message: str) -> SysmonHealthApplyResult:
        result.steps.append(SysmonHealthStep(name=name, status=step_status, detail=detail))
        result.message = message
        return result

    if not GROUP_NAME_RE.match(status.group):
        return stop("group", "failed", f"{status.group!r} is not a valid Wazuh group name.", "Nothing done: invalid group name.")
    if status.read_errors:
        return stop(
            "read",
            "failed",
            " ".join(status.read_errors),
            "Nothing done: some state could not be read, so nothing is changed on guesswork.",
        )
    if not status.group_exists:
        return stop("group", "failed", f"Wazuh group {status.group} does not exist.", "Nothing done: the group does not exist.")

    # 1. Rules (per manager). Everything else waits for them.
    if status.rules.current:
        result.steps.append(SysmonHealthStep(name="rules", status="ok", detail="Present on the manager and current."))
    elif not install_rules_if_needed:
        return stop(
            "rules",
            "skipped",
            f"{RULES_FILENAME} is {'outdated' if status.rules.present else 'missing'}; re-run with install_rules=true (restarts the manager).",
            "Stopped: the sensor-health rules must be on the manager before the endpoint pieces.",
        )
    elif dry_run:
        result.steps.append(
            SysmonHealthStep(name="rules", status="planned", detail="Upload, validate, restart the manager, confirm the restart."),
        )
    else:
        step = await install_rules()
        result.steps.append(step)
        if step.status == "failed":
            result.message = "Stopped: the rules could not be installed."
            return result

    # 2. Shared scripts.
    stale = [state.name for state in status.shared_files if not state.current]
    scripts_ok = {state.name: state.current for state in status.shared_files}
    if not stale:
        result.steps.append(SysmonHealthStep(name="shared_files", status="ok", detail="Both scripts are current."))
    elif dry_run:
        result.steps.append(SysmonHealthStep(name="shared_files", status="planned", detail=f"Publish {', '.join(stale)} via WAZUH-UTILS."))
        scripts_ok.update({name: True for name in stale})
    else:
        published, detail = await publish_shared_scripts(status.group, stale)
        if published:
            verified = await shared_script_states(status.group)
            bad = [state for state in verified if state.name in stale and not state.current]
            if bad:
                observed = ", ".join(f"{state.name} sha256={state.sha256 or state.read_error}" for state in bad)
                logger.error(f"Sysmon health: published scripts to {status.group} but the manager reports different content: {observed}")
                published, detail = False, f"Published, but the manager reports different content: {observed}."
            scripts_ok.update({state.name: state.current for state in verified})
        if not published:
            return stop(
                "shared_files",
                "failed",
                detail,
                "Stopped: the scripts are not verified in the shared folder, so agent.conf was not touched.",
            )
        result.steps.append(SysmonHealthStep(name="shared_files", status="changed", detail=detail))

    # 3. agent.conf.
    wanted = wanted_wodles(True, scripts_ok, status.sysmon_config_present)
    current = await _get_agent_conf(status.group)
    if current is None:
        return stop("agent_conf", "failed", "Could not read the group's agent.conf.", "Stopped: agent.conf could not be read.")
    try:
        updated = reconcile_agent_conf(current, wanted)
    except ValueError as e:
        return stop("agent_conf", "failed", str(e), "Stopped: agent.conf needs a manual fix.")
    result.agent_conf_diff = unified_diff(current, updated)
    held_back = "" if RELOAD_TAG in wanted else " sysmon-reload is held back until a sysmon_config.xml is deployed."
    if same_agent_conf(updated, current):
        result.steps.append(
            SysmonHealthStep(name="agent_conf", status="ok", detail=f"Already has {sorted(wanted) or 'no managed wodles'}.{held_back}"),
        )
    elif dry_run:
        result.steps.append(SysmonHealthStep(name="agent_conf", status="planned", detail=f"Write {sorted(wanted)}.{held_back}"))
    else:
        # Re-read right before writing: an admin may have edited agent.conf in the Groups editor meanwhile.
        if not same_agent_conf(await _get_agent_conf(status.group), current):
            return stop("agent_conf", "failed", "agent.conf changed while applying; run again.", "Stopped: concurrent agent.conf change.")
        response = await _put_agent_conf(status.group, updated)
        if not _wazuh_ok(response):
            return stop(
                "agent_conf",
                "failed",
                f"The manager refused agent.conf: {_wazuh_message(response)}",
                "Stopped: agent.conf was not accepted.",
            )
        # The API re-indents what it stores, so compare ignoring indentation.
        if not same_agent_conf(await _get_agent_conf(status.group), updated):
            return stop("agent_conf", "failed", "agent.conf was accepted but reads back differently.", "agent.conf did not stick.")
        result.steps.append(
            SysmonHealthStep(
                name="agent_conf",
                status="changed",
                detail=f"Wrote {sorted(wanted)}; agents in the group will restart to apply it.{held_back}",
            ),
        )

    result.success = True
    result.message = "Planned (dry run)." if dry_run else "Applied."
    if not dry_run:
        result.status = await get_sysmon_health_status(result.customer_code, session)
    return result


async def apply_sysmon_health(
    customer_code: str,
    session: AsyncSession,
    dry_run: bool = True,
    install_rules_if_needed: bool = False,
) -> SysmonHealthApplyResult:
    """Bring one customer's Windows group up to date. Dry run by default; only installs rules when asked to."""
    result = SysmonHealthApplyResult(success=False, customer_code=customer_code, group=windows_group(customer_code), dry_run=dry_run)
    try:
        async with SYSMON_HEALTH_LOCK:
            return await _apply_unlocked(result, session, install_rules_if_needed)
    except SysmonHealthAssetError as e:
        logger.error(f"Sysmon health: {e}")
        result.steps.append(SysmonHealthStep(name="assets", status="failed", detail=str(e)))
        result.message = "Stopped: vendored assets failed their integrity check."
        return result


async def apply_sysmon_health_all(
    session: AsyncSession,
    dry_run: bool = True,
    install_rules_if_needed: bool = False,
    on_rules_step: Optional[Callable[[SysmonHealthStep], Awaitable[None]]] = None,
    on_result: Optional[Callable[[SysmonHealthApplyResult], Awaitable[None]]] = None,
) -> SysmonHealthApplyAllResult:
    """
    The backfill: every customer with a Wazuh group. The rules (per manager) are handled once, first.

    ``on_rules_step`` / ``on_result`` are awaited as each piece completes (the route audits there), so a failure part
    way through still leaves a record of what was already changed.
    """
    result = SysmonHealthApplyAllResult(success=False, dry_run=dry_run)
    try:
        rules = await rules_state()
        if not rules.readable:
            result.rules_step = SysmonHealthStep(name="rules", status="failed", detail=f"Could not read the rules file: {rules.read_error}")
        elif rules.current:
            result.rules_step = SysmonHealthStep(name="rules", status="ok", detail="Present on the manager and current.")
        elif not install_rules_if_needed:
            result.rules_step = SysmonHealthStep(
                name="rules",
                status="skipped",
                detail="Missing or outdated; re-run with install_rules=true (restarts the manager).",
            )
        elif dry_run:
            result.rules_step = SysmonHealthStep(
                name="rules",
                status="planned",
                detail="Upload, validate, restart the manager, confirm the restart.",
            )
        else:
            async with SYSMON_HEALTH_LOCK:
                # Re-check under the lock: a concurrent run may have just installed them (no second restart).
                if (await rules_state()).current:
                    result.rules_step = SysmonHealthStep(name="rules", status="ok", detail="Installed by a concurrent run.")
                else:
                    result.rules_step = await install_rules()
            if on_rules_step:
                await on_rules_step(result.rules_step)
    except SysmonHealthAssetError as e:
        result.rules_step = SysmonHealthStep(name="rules", status="failed", detail=str(e))

    if result.rules_step.status in ("failed", "skipped"):
        result.message = "Stopped: the sensor-health rules are not in place on the manager."
        return result

    metas = (await session.execute(select(CustomersMeta))).scalars().all()
    for meta in metas:
        if not meta.customer_meta_wazuh_group:
            continue
        # In a dry run with planned rules, report each group as if the rules were in place.
        item = await apply_sysmon_health(
            meta.customer_code,
            session,
            dry_run=dry_run,
            install_rules_if_needed=dry_run and install_rules_if_needed,
        )
        result.results.append(item)
        if on_result:
            await on_result(item)
    result.success = all(item.success for item in result.results)
    done = sum(1 for item in result.results if item.success)
    result.message = f"{done}/{len(result.results)} customer group(s) {'would be' if dry_run else 'are'} up to date."
    return result


async def provisioning_wodles(group: str) -> Tuple[Set[str], Optional[str]]:
    """
    For a NEW customer's Windows group: publish the scripts and return which managed wodles the template may keep.

    Never installs rules (that restarts the manager for every customer on it) and never raises: a missing prerequisite
    just leaves the wodle out, and the admin backfill adds it later. A new group has no sysmon_config.xml yet, so the
    reload wodle is always held back here.

    Returns ``(wodles, reason)``: ``reason`` says why the sysmon-watchdog wodle was left out (also logged at WARNING),
    and is None when it is kept.
    """
    wanted: Set[str] = set()
    reason = None
    try:
        rules = await rules_state()
        if not rules.readable:
            reason = f"{RULES_FILENAME} could not be read on the manager ({rules.read_error})"
        elif not rules.current:
            reason = f"{RULES_FILENAME} is {'outdated' if rules.present else 'missing'} on the manager"
        else:
            published, detail = await publish_shared_scripts(group)
            if not published:
                reason = f"the scripts were not published to the group's shared folder: {detail}"
            else:
                scripts_ok = {state.name: state.current for state in await shared_script_states(group)}
                wanted = wanted_wodles(True, scripts_ok, sysmon_config_present=False)
                if WATCHDOG_TAG not in wanted:
                    reason = f"{WATCHDOG_SCRIPT} was published but could not be verified in the group's shared folder"
    except Exception as e:  # noqa: BLE001 - provisioning must not fail on an optional feature
        wanted, reason = set(), f"the provisioning check failed: {e}"
    if reason:
        logger.warning(
            f"Sysmon health: {group} is provisioned without the sysmon-watchdog wodle: {reason}. "
            "The Sysmon health apply adds it once that is fixed.",
        )
    return wanted, reason
