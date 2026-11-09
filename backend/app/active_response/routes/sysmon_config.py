import hashlib
from typing import Optional
from typing import Tuple

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import Security
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.routes.sysmon_health import _audit_payload
from app.active_response.schema.sysmon_config import SysmonConfigContentResponse
from app.active_response.schema.sysmon_config import SysmonConfigDeploymentResult
from app.active_response.schema.sysmon_config import SysmonConfigListResponse
from app.active_response.schema.sysmon_config import SysmonConfigUploadResponse
from app.active_response.schema.sysmon_config import SysmonDefaultConfigResponse
from app.active_response.schema.sysmon_config import SysmonDefaultConfigSaveRequest
from app.active_response.schema.sysmon_config import SysmonDefaultConfigSaveResponse
from app.active_response.schema.sysmon_health import SysmonHealthApplyResult
from app.active_response.services.sysmon_config import INSTALL_DIR_PLACEHOLDER
from app.active_response.services.sysmon_config import MAX_SYSMON_CONFIG_BYTES
from app.active_response.services.sysmon_config import check_config_exists
from app.active_response.services.sysmon_config import deploy_sysmon_config_to_worker
from app.active_response.services.sysmon_config import render_default_config
from app.active_response.services.sysmon_config import templatize_install_dir
from app.active_response.services.sysmon_config import validate_sysmon_config
from app.active_response.services.sysmon_health import RELOAD_TAG
from app.active_response.services.sysmon_health import SYSMON_HEALTH_LOCK
from app.active_response.services.sysmon_health import apply_sysmon_health
from app.active_response.services.sysmon_health import get_sysmon_health_status
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.data_store.data_store_operations import SYSMON_CONFIG_DEFAULT_OBJECT
from app.data_store.data_store_operations import SYSMON_CONFIG_DEFAULTS_BUCKET
from app.data_store.data_store_operations import download_sysmon_config
from app.data_store.data_store_operations import list_sysmon_configs
from app.data_store.data_store_operations import read_default_sysmon_config
from app.data_store.data_store_operations import upload_sysmon_config
from app.data_store.data_store_operations import write_default_sysmon_config
from app.db.db_session import get_db
from app.middleware.customer_access import scoped_customer_codes
from app.middleware.customer_access import verify_customer_code_access

sysmon_config_router = APIRouter()

# Uploading a customer's config stays admin; a responder may read the configs of their
# customers and deploy them (#1219).


@sysmon_config_router.post(
    "/upload",
    response_model=SysmonConfigUploadResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def upload_customer_sysmon_config(
    customer_code: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    """Upload a sysmon config XML file for a specific customer."""
    # Validate file extension
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=400, detail="Only XML files are accepted for sysmon configs")

    try:
        # Read and validate file content
        file_content = await file.read()
        xml_content = file_content.decode("utf-8")
        await validate_sysmon_config(xml_content)

        # Reset file pointer for upload
        await file.seek(0)

        # Check if file exists already
        file_exists = await check_config_exists(customer_code)

        # Upload file
        await upload_sysmon_config(customer_code, file)

        return SysmonConfigUploadResponse(
            success=True,
            message=f"Successfully {'updated' if file_exists else 'uploaded'} Sysmon config",
            customer_code=customer_code,
            filename="sysmon_config.xml",
            overwritten=file_exists,
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 encoded text")


# This CoPilot's default Sysmon config, which pre-fills "Add new Configuration". It is the installer's template: its
# install-folder paths keep the __INSTALLDIRNAME__ placeholder, which the editor gets replaced with the new customer's
# code. It lives in a bucket of its own, so deploys (which read the customer's stored copy) never see it.
# Admin only, like uploading a customer's config. These routes must come before the /{customer_code} route, which
# would otherwise take "default-config" for a customer code.
NO_DEFAULT_MESSAGE = 'No default Sysmon config is set on this CoPilot. An admin can set one with "Save as default".'


@sysmon_config_router.get(
    "/default-config",
    response_model=SysmonDefaultConfigResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_sysmon_default_config(
    customer_code: Optional[str] = Query(
        None,
        description=f"Render the default for this customer: its code replaces each {INSTALL_DIR_PLACEHOLDER} placeholder.",
    ),
):
    """This CoPilot's default Sysmon config, rendered for a customer when a customer code is given."""
    try:
        stored = await read_default_sysmon_config()
    except Exception as e:  # noqa: BLE001 - a read failure is reported as one, never as "no default"
        logger.error(f"Could not read this CoPilot's default Sysmon config: {e}")
        raise HTTPException(status_code=502, detail=f"Could not read this CoPilot's default Sysmon config from its data store (MinIO): {e}")
    if stored is None:
        return SysmonDefaultConfigResponse(success=True, message=NO_DEFAULT_MESSAGE, present=False)

    try:
        template = stored.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=500,
            detail='This CoPilot\'s default Sysmon config is not valid UTF-8 text. An admin can replace it with "Save as default".',
        )
    placeholders = template.count(INSTALL_DIR_PLACEHOLDER)
    if not customer_code:
        return SysmonDefaultConfigResponse(
            success=True,
            message="Retrieved this CoPilot's default Sysmon config",
            present=True,
            config_content=template,
            placeholders=placeholders,
        )
    # Without a placeholder nothing is rendered: the default comes back as stored, with whatever install-folder paths it
    # was saved with (possibly another customer's). rendered_for stays unset, so the editor says to check them.
    if not placeholders:
        return SysmonDefaultConfigResponse(
            success=True,
            message=(
                f"Retrieved this CoPilot's default Sysmon config. It has no {INSTALL_DIR_PLACEHOLDER} placeholder, so its "
                f"install-folder paths were not set for {customer_code}."
            ),
            present=True,
            config_content=template,
            placeholders=0,
        )
    return SysmonDefaultConfigResponse(
        success=True,
        message=f"Retrieved this CoPilot's default Sysmon config, rendered for {customer_code}",
        present=True,
        config_content=render_default_config(template, customer_code),
        rendered_for=customer_code,
        placeholders=placeholders,
    )


def _default_saved_message(placeholders: int, restored: int, customer_code: Optional[str]) -> str:
    if not placeholders:
        return (
            f"Saved this CoPilot's default Sysmon config. It has no {INSTALL_DIR_PLACEHOLDER} placeholder, so every new "
            "configuration will get these exact install-folder paths."
        )
    turned_back = f', {restored} of them turned back from "{customer_code}"' if restored else ""
    return (
        f"Saved this CoPilot's default Sysmon config: {placeholders} {INSTALL_DIR_PLACEHOLDER} "
        f"placeholder{'' if placeholders == 1 else 's'}{turned_back}. \"Add new Configuration\" fills them in with each new "
        "customer's code."
    )


@sysmon_config_router.put(
    "/default-config",
    response_model=SysmonDefaultConfigSaveResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def save_sysmon_default_config(
    body: SysmonDefaultConfigSaveRequest,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    """
    Replace this CoPilot's default Sysmon config. No customer's stored config changes.

    With customer_code, the content is the editor's copy for that customer: its install-folder paths
    (\\Program Files\\<customer_code>\\) are turned back into the placeholder first, so each new customer gets their own.
    """
    content, restored = templatize_install_dir(body.config_content, body.customer_code)
    try:
        data = content.encode("utf-8")
    except UnicodeEncodeError:
        raise HTTPException(status_code=400, detail="The config is not valid UTF-8 text")
    if len(data) > MAX_SYSMON_CONFIG_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"The config is {len(data)} bytes, over the {MAX_SYSMON_CONFIG_BYTES} bytes (5 MiB) the Wazuh sidecar accepts for "
                "a deploy. Nothing was saved."
            ),
        )
    # A customer's upload's checks, except the installer-token one: the default keeps its placeholders
    await validate_sysmon_config(content, allow_installer_tokens=True)

    placeholders = content.count(INSTALL_DIR_PLACEHOLDER)
    # Identifies what was saved without keeping the config itself
    saved = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "placeholders": placeholders,
        "restored": restored,
        "customer_code": body.customer_code,
    }
    audit = {
        "action": AuditAction.SYSMON_CONFIG_DEFAULT_SAVE,
        "actor_user_id": current_user.id,
        "actor_username": current_user.username,
        "entity_type": "sysmon_config_default",
        "entity_id": f"{SYSMON_CONFIG_DEFAULTS_BUCKET}/{SYSMON_CONFIG_DEFAULT_OBJECT}",
        "new_value": saved,
        "request": request,
    }
    try:
        await write_default_sysmon_config(data)
    except Exception as e:  # noqa: BLE001 - audited, then reported
        logger.error(f"Could not save this CoPilot's default Sysmon config: {e}")
        await record_audit_event(**audit, result=AuditResult.FAILURE, details=f"Could not store it: {e}"[:1000])
        raise HTTPException(status_code=502, detail=f"Could not save this CoPilot's default Sysmon config to its data store (MinIO): {e}")
    await record_audit_event(**audit, result=AuditResult.SUCCESS)

    return SysmonDefaultConfigSaveResponse(
        success=True,
        message=_default_saved_message(placeholders, restored, body.customer_code),
        placeholders=placeholders,
        restored=restored,
    )


# This route must come before the /{customer_code} route
@sysmon_config_router.get(
    "/content/{customer_code}",
    response_model=SysmonConfigContentResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder")), Depends(verify_customer_code_access)],
)
async def get_customer_sysmon_config_content(customer_code: str, session: AsyncSession = Depends(get_db)):
    """Get the sysmon config for a specific customer as a string."""
    try:
        data_bytes = await download_sysmon_config(customer_code)
        xml_content = data_bytes.decode("utf-8")

        return SysmonConfigContentResponse(
            success=True,
            message="Successfully retrieved Sysmon config",
            customer_code=customer_code,
            config_content=xml_content,
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=500, detail="Failed to decode config file as UTF-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")


@sysmon_config_router.get(
    "",
    response_model=SysmonConfigListResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder"))],
)
async def get_all_sysmon_configs(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List the customers that have sysmon configs, among those the caller may see."""
    customers = await list_sysmon_configs()
    allowed = await scoped_customer_codes(current_user, None, session)
    if allowed is not None:
        customers = [code for code in customers if code in allowed]

    return SysmonConfigListResponse(
        success=True,
        message="Successfully retrieved list of customer sysmon configs",
        customer_codes=customers,
    )


@sysmon_config_router.get(
    "/{customer_code}",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder")), Depends(verify_customer_code_access)],
)
async def get_customer_sysmon_config(customer_code: str, session: AsyncSession = Depends(get_db)):
    """Download the sysmon config for a specific customer."""
    try:
        data = await download_sysmon_config(customer_code)
        return Response(
            content=data,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=sysmon_config_{customer_code}.xml"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")


@sysmon_config_router.post(
    "/deploy/{customer_code}",
    response_model=SysmonConfigDeploymentResult,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder")), Depends(verify_customer_code_access)],
)
async def deploy_sysmon_config(
    customer_code: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Deploy a customer's Sysmon config to the Wazuh master.
    Fetches the config from MinIO storage, validates it, and sends it to the Wazuh master.
    The agents apply it through the sysmon-reload wodle: after a successful deploy, an admin's call also runs the
    Sysmon health apply (see _enable_sysmon_reload), which adds that wodle to the group's agent.conf.
    The Wazuh Master needs to be running the Customer-Provisioning-Worker application.
    Currently we are invoking this via a wodle command that must be placed in the wazuh agent group.
    <wodle name="command">
                <disabled>no</disabled>
                <tag>sysmon-reload</tag>
                <command>"C:\Program Files (x86)\ossec-agent\active-response\bin\run_sysmon_config_reload.cmd"</command>
                <interval>24h</interval>
                <ignore_output>yes</ignore_output>
                <run_on_start>yes</run_on_start>
                <timeout>0</timeout>
        </wodle>
    Might revisit in the future to use the Wazuh API directly to invoke the active response.
    The current limitation with the active-response is that we have to wait for the manager to pass the new sysmon_config.xml
    file to the agent.
    I.E:
    {
    "endpoint": "/active-response",
    "arguments": [],
    "command": "sysmon_config_reload",
    "custom": true,
    "alert": {
        "action": "sysmon_config_reload"
    },
    "params": {
        "wait_for_complete": true,
        "agents_list": ["085"]
    }
    }
    """
    result = None
    try:
        result = await deploy_sysmon_config_to_worker(customer_code=customer_code, session=session)
    finally:
        # Written after the deploy, with its outcome (the service reports failures rather than raising).
        await record_audit_event(
            action=AuditAction.SYSMON_CONFIG_DEPLOY,
            actor_user_id=current_user.id,
            actor_username=current_user.username,
            customer_code=customer_code,
            entity_type="sysmon_config",
            entity_id=customer_code,
            result=AuditResult.SUCCESS if result is not None and result.success else AuditResult.FAILURE,
            details=None if result is None or result.success else result.message,
            request=request,
        )
    if result.success:
        result.sysmon_health, result.sysmon_health_warning = await _enable_sysmon_reload(customer_code, request, current_user, session)
    return result


def _reload_warning(health: SysmonHealthApplyResult) -> Optional[str]:
    """Why the endpoints will not pick the deployed config up after this apply; None when nothing stands in the way."""
    reason = f"{health.message} {health.steps[-1].detail if health.steps else ''}".strip()
    if health.status is None or health.status.read_errors:
        return (
            "Could not confirm that the endpoints will apply this config: the group's state could not be read, so it is "
            f"unknown whether {health.group}'s agent.conf has the sysmon-reload wodle. {reason}"
        )
    if RELOAD_TAG not in health.status.wodles_present:
        return (
            "Endpoints will not apply this config until the Sysmon health apply succeeds: the sysmon-reload wodle, which "
            f"applies the deployed config on each agent, is not in {health.group}'s agent.conf. {reason}"
        )
    if not health.success:
        return f"The Sysmon health apply did not complete, but the group's sysmon-reload wodle will still apply this config. {reason}"
    return None


async def _enable_sysmon_reload(
    customer_code: str,
    request: Request,
    current_user: User,
    session: AsyncSession,
) -> Tuple[Optional[SysmonHealthApplyResult], Optional[str]]:
    """
    After a successful deploy: the agents only pick sysmon_config.xml up through a sysmon-reload wodle in the group's
    agent.conf. What happens depends on the group:

    - It already has one (CoPilot-managed, or hand-added on an existing customer): it applies the config. Nothing else
      is touched.
    - It carries CoPilot's SYSMON-HEALTH block (provisioned or applied after Phase 0: a new customer): an admin's
      deploy runs the Sysmon health apply, which adds the reload. It never installs the rules (that restarts the
      manager) and is skipped while another apply holds the lock, rather than waiting behind it.
    - Anything else predates Phase 0 (an existing customer): its agent.conf is left alone, because rewriting it
      restarts every agent in the group. Enabling the reload there stays an explicit admin action, and the warning
      says how.

    Returns the apply result (when one ran) and a warning when the endpoints will not, or may not, apply the config.
    """
    apply_hint = f"POST /api/sysmon_config/health/{customer_code}/apply?dry_run=false"
    try:
        status = await get_sysmon_health_status(customer_code, session)
    except Exception as e:  # noqa: BLE001 - the deploy itself succeeded; only the check failed
        logger.error(f"Sysmon config deploy: could not check {customer_code}'s Windows group: {e}")
        status = None
    if status is None or status.read_errors:
        return None, (
            "Could not read the group's agent.conf, so it is unknown whether the endpoints will apply this config (that "
            f"needs a sysmon-reload wodle in it). Check with GET /api/sysmon_config/health/{customer_code}."
        )
    if RELOAD_TAG in status.wodles_present:
        return None, None
    if not status.managed_block_present:
        return None, (
            f"Endpoints will not apply this config yet: {status.group}'s agent.conf has no sysmon-reload wodle and no "
            "CoPilot-managed Sysmon health block (the group predates it, or was provisioned without the watchdog), so the "
            "deploy left its agent.conf alone. An admin can enable the "
            f"reload with the Sysmon health apply ({apply_hint}; preview it first without dry_run=false). That rewrites "
            "agent.conf and restarts the group's agents."
        )
    if current_user.role_id != RoleEnum.admin:
        return None, (
            "Endpoints will not apply this config until the group's agent.conf has the sysmon-reload wodle, which applies "
            f"the deployed config on each agent. An admin adds it by deploying the config again, or with {apply_hint}."
        )
    if SYSMON_HEALTH_LOCK.locked():
        return None, (
            "Endpoints will not apply this config yet: another Sysmon health apply is running, so the sysmon-reload wodle "
            f"was not added. Deploy again once it has finished, or run {apply_hint}."
        )

    try:
        health = await apply_sysmon_health(customer_code, session, dry_run=False, install_rules_if_needed=False)
    except Exception as e:  # noqa: BLE001 - the deploy itself succeeded; report the apply, don't 500
        logger.error(f"Sysmon config deploy: the Sysmon health apply for {customer_code} failed: {e}")
        return None, f"Endpoints will not apply this config until the Sysmon health apply succeeds; it could not run: {e}"
    await record_audit_event(
        action=AuditAction.SYSMON_HEALTH_APPLY,
        actor_user_id=current_user.id,
        actor_username=current_user.username,
        customer_code=customer_code,
        entity_type="wazuh_group",
        entity_id=health.group,
        result=AuditResult.SUCCESS if health.success else AuditResult.FAILURE,
        new_value=_audit_payload(health, install_rules=False),
        request=request,
    )
    return health, _reload_warning(health)
