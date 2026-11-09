from typing import Optional
from typing import Tuple

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
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
from app.active_response.schema.sysmon_health import SysmonHealthApplyResult
from app.active_response.services.sysmon_config import check_config_exists
from app.active_response.services.sysmon_config import deploy_sysmon_config_to_worker
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
from app.data_store.data_store_operations import download_sysmon_config
from app.data_store.data_store_operations import list_sysmon_configs
from app.data_store.data_store_operations import upload_sysmon_config
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
