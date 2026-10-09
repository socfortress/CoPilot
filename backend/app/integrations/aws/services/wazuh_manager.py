"""Applying an AWS instance's buckets to the Wazuh manager, and reading back what the module said.

The Wazuh API can only replace ossec.conf as a whole, so every write is guarded so that it can never
amount to more than this instance's `<bucket>` entries:

1. **Read** the live file and **reconcile** this instance's buckets into it
   (`reconcile_aws_buckets`, which itself refuses a result that differs from the live file in
   anything else — `verify_only_instance_changed`).
2. **Re-read** right before writing. If the file changed in between (another deployment, an
   Office365 provisioning, an engineer), nothing is written: the edit was based on a stale copy and
   would undo theirs. One fresh attempt is made, then the deployment fails.
3. **Write**, then ask the manager to **validate** the new file before anything restarts. If it is
   invalid — or the manager cannot say — the original file is written back, so the manager is never
   restarted onto a configuration it would refuse to start with.
4. **Restart** only after a clean validation.

The original configuration is held in memory only, never written to disk: it carries every
customer's credentials. Every step runs under one lock, so two AWS deployments in this process
cannot interleave (Office365 provisioning does not take it, which is what step 2 is for).
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.integrations.aws.schema.provision import AwsConfigNotice
from app.integrations.aws.services.wazuh_config import AwsWazuhConfigError
from app.integrations.aws.services.wazuh_config import ReconcileResult
from app.integrations.aws.services.wazuh_config import reconcile_aws_buckets

WAZUH_CONFIG_LOCK = asyncio.Lock()

AWS_MODULE_LOG_TAG = "wazuh-modulesd:aws-s3"
# What the wodle prints (and modulesd relays as a WARNING) when `/root/.aws/config` exists without the
# profile a bucket needs — `[default]` for every bucket without `aws_profile`. It then exits with 23.
PROFILE_ERROR_TEXT = "No profile named"
# Logged when a run over every bucket completes; past this point no exit-23 is coming for this restart.
RUN_FINISHED_TEXT = "Fetching logs finished"

# How long to watch the manager's log for the exit-23 error after a restart.
PROFILE_CHECK_TIMEOUT_SECONDS = 60
PROFILE_CHECK_INTERVAL_SECONDS = 10


async def get_manager_configuration() -> str:
    response = await send_get_request(endpoint="/manager/configuration", params={"raw": True})
    if not response or not response.get("success") or "data" not in response:
        raise HTTPException(
            status_code=502,
            detail=f"Could not read the Wazuh manager's ossec.conf: {(response or {}).get('message', 'no response')}",
        )
    return response["data"]


async def push_manager_configuration(config: str) -> None:
    response = await send_put_request(
        endpoint="/manager/configuration",
        data=config.encode("utf-8"),
        binary_data=True,
    )
    if not (response and response.get("success") and response.get("data", {}).get("error") == 0):
        # The message is the manager's own validation error; the configuration itself is never echoed.
        raise HTTPException(
            status_code=502,
            detail=f"The Wazuh manager rejected the new ossec.conf: {(response or {}).get('message', 'no response')}",
        )


async def restart_manager() -> None:
    logger.info("Restarting the Wazuh manager to apply the aws-s3 configuration.")
    await send_put_request(endpoint="/manager/restart", data=None)


async def validate_manager_configuration() -> Optional[str]:
    """
    Ask the manager whether the ossec.conf on disk is valid. ``None`` when it is, otherwise why not.

    An unanswered question counts as invalid: restarting onto a configuration nobody has checked is
    exactly the risk this exists to avoid.
    """
    response = await send_get_request(endpoint="/manager/configuration/validation")
    if not response or not response.get("success"):
        return f"the manager could not validate it ({(response or {}).get('message', 'no response')})"
    data = (response.get("data") or {}).get("data") or {}
    if data.get("total_failed_items", 0) or data.get("failed_items"):
        return f"the manager reported it invalid: {data.get('failed_items')}"
    statuses = {item.get("status") for item in data.get("affected_items", [])}
    if statuses and statuses != {"OK"}:
        return f"the manager reported it invalid: {data.get('affected_items')}"
    return None


async def _write_guarded(original: str, updated: str) -> None:
    """Write ``updated``, keeping the manager on ``original`` unless the new file validates."""
    try:
        await push_manager_configuration(updated)
    except HTTPException:
        # Wazuh validates on upload and keeps the old file when it refuses one; confirm that rather
        # than assume it, and put the original back if the file did change.
        current = await get_manager_configuration()
        if current != original:
            await push_manager_configuration(original)
        raise

    problem = await validate_manager_configuration()
    if problem:
        logger.error(f"The new ossec.conf did not validate ({problem}); restoring the previous configuration.")
        await push_manager_configuration(original)
        raise HTTPException(
            status_code=502,
            detail=f"The new ossec.conf did not validate: {problem}. The previous configuration was restored and the manager was not restarted.",
        )


async def apply_instance_buckets(
    desired: List[ET.Element],
    bucket_name: str,
    account_id: str,
    adopt_existing: bool,
    keep_only_logs_after: bool = True,
) -> ReconcileResult:
    """Reconcile one instance's buckets on the manager; writes and restarts only when something changed."""
    async with WAZUH_CONFIG_LOCK:
        for attempt in (1, 2):
            raw = await get_manager_configuration()
            try:
                result = reconcile_aws_buckets(
                    raw,
                    desired,
                    bucket_name,
                    account_id,
                    adopt_existing=adopt_existing,
                    keep_only_logs_after=keep_only_logs_after,
                )
            except AwsWazuhConfigError as e:
                raise HTTPException(status_code=400, detail=str(e))

            if not result.changed:
                logger.info(f"aws-s3 buckets for {bucket_name} / {account_id} already match; the Wazuh manager is not restarted.")
                return result

            if await get_manager_configuration() == raw:
                break
            logger.warning(f"ossec.conf changed while it was being edited (attempt {attempt}); starting over from the new file.")
        else:
            raise HTTPException(
                status_code=409,
                detail="ossec.conf kept changing on the Wazuh manager while CoPilot was editing it; nothing was written. Try again.",
            )

        await _write_guarded(raw, result.config)
        logger.info(
            f"aws-s3 buckets for {bucket_name} / {account_id}: added {result.added}, updated {result.updated}, removed {result.removed}.",
        )
        await restart_manager()
        return result


# ---------------------------------------------------------------------------------------------
# /root/.aws/config (exit code 23)
# ---------------------------------------------------------------------------------------------


async def _latest_log_timestamp(search: str) -> Optional[str]:
    response = await send_get_request(
        endpoint="/manager/logs",
        params={"tag": AWS_MODULE_LOG_TAG, "search": search, "sort": "-timestamp", "limit": 1},
    )
    if not response or not response.get("success"):
        return None
    items = (response.get("data") or {}).get("data", {}).get("affected_items", [])
    return items[0].get("timestamp") if items else None


def _is_after(timestamp: Optional[str], marker: Optional[str]) -> bool:
    if not timestamp:
        return False
    if not marker:
        return True
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")) > datetime.fromisoformat(marker.replace("Z", "+00:00"))
    except ValueError:
        return timestamp > marker


async def log_markers() -> tuple:
    """The newest exit-23 and run-finished log entries *before* a change, so later ones can be told apart."""
    return await _latest_log_timestamp(PROFILE_ERROR_TEXT), await _latest_log_timestamp(RUN_FINISHED_TEXT)


async def wait_for_profile_error(markers: tuple) -> bool:
    """
    Watch the manager's log after a restart for the exit-23 error. True when it appeared.

    Best effort: stops early once a full run has finished cleanly, and gives up after
    `PROFILE_CHECK_TIMEOUT_SECONDS` (the manager's API is unavailable for part of a restart, and a
    long first run may not finish in time). Absence of the error is therefore not proof.
    """
    error_marker, finished_marker = markers
    waited = 0
    while waited < PROFILE_CHECK_TIMEOUT_SECONDS:
        await asyncio.sleep(PROFILE_CHECK_INTERVAL_SECONDS)
        waited += PROFILE_CHECK_INTERVAL_SECONDS
        if _is_after(await _latest_log_timestamp(PROFILE_ERROR_TEXT), error_marker):
            logger.warning("The aws-s3 module reported a missing [default] profile in /root/.aws/config after the restart.")
            return True
        if _is_after(await _latest_log_timestamp(RUN_FINISHED_TEXT), finished_marker):
            return False
    return False


def aws_config_notice(detected: bool, region: Optional[str]) -> AwsConfigNotice:
    """
    The manual step CoPilot cannot do: give `/root/.aws/config` a `[default]` section.

    Shown after every AWS deployment, because CoPilot cannot see the file: the Wazuh API reads and
    writes `ossec.conf` only. Any region works for S3 (the client follows the bucket's region); the
    bucket's own region is suggested when validation found it.
    """
    region = region or "us-east-1"
    contents = f"[default]\nregion = {region}\n"
    if detected:
        summary = (
            "Action required: the Wazuh manager's aws-s3 module stopped with exit code 23 because /root/.aws/config exists "
            "but has no [default] section. No AWS logs are collected until it is fixed. CoPilot cannot edit that file "
            "through the Wazuh API, so add the section below by hand."
        )
    else:
        summary = (
            "CoPilot cannot read or write /root/.aws/config on the Wazuh master — the Wazuh API only edits ossec.conf. "
            "If that file exists, it must contain a [default] section, or the aws-s3 module exits with code 23 and "
            "collects nothing. If the file does not exist, nothing needs doing."
        )
    return AwsConfigNotice(
        detected=detected,
        summary=summary,
        steps=[
            "Log in to the Wazuh master node (the manager CoPilot's Wazuh Manager connector points at).",
            "Check whether the file exists: sudo ls -l /root/.aws/config",
            "If it exists and has no [default] section, append the section below, leaving any existing [profile …] sections as they are: "
            "sudo vi /root/.aws/config",
            "Restart the manager so the module retries straight away: sudo systemctl restart wazuh-manager",
            "Confirm in /var/ossec/logs/ossec.log that wazuh-modulesd:aws-s3 no longer reports 'No profile named'.",
        ],
        contents=contents,
    )
