from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_health import SysmonHealthApplyAllResult
from app.active_response.schema.sysmon_health import SysmonHealthApplyResult
from app.active_response.schema.sysmon_health import SysmonHealthStatus
from app.active_response.schema.sysmon_health import SysmonHealthStep
from app.active_response.services.sysmon_health import RULES_FILENAME
from app.active_response.services.sysmon_health import apply_sysmon_health
from app.active_response.services.sysmon_health import apply_sysmon_health_all
from app.active_response.services.sysmon_health import asset_version
from app.active_response.services.sysmon_health import get_sysmon_health_status
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

# Phase 0 Sysmon sensor health: the watchdog / reload wodles, their scripts and the sensor-health rules, for a
# customer's Windows group. Admin only: applying writes agent.conf (restarting the group's agents) and can restart
# the manager.
sysmon_health_router = APIRouter()

DRY_RUN_HELP = "Report what would change without changing anything. Defaults to true."
INSTALL_RULES_HELP = (
    "Install sysmon_sensor_health_rules.xml when it is missing or outdated. This restarts the Wazuh manager (the whole "
    "cluster when clustered), which briefly pauses analysis for every customer on it."
)


def _audit_payload(result: SysmonHealthApplyResult, install_rules: bool) -> dict:
    return {
        "dry_run": result.dry_run,
        "install_rules": install_rules,
        "steps": [{"name": step.name, "status": step.status} for step in result.steps],
        "assets": asset_version(),
    }


@sysmon_health_router.post(
    "/apply-all",
    response_model=SysmonHealthApplyAllResult,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def apply_sysmon_health_to_all_customers(
    request: Request,
    dry_run: bool = Query(True, description=DRY_RUN_HELP),
    install_rules: bool = Query(False, description=INSTALL_RULES_HELP),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Backfill every customer's Windows group. The rules are handled once, first; groups are then done one by one."""

    async def audit_rules_step(step: SysmonHealthStep) -> None:
        # The manager-wide rules install (a manager restart) gets its own row, written as soon as it is done.
        await record_audit_event(
            action=AuditAction.SYSMON_HEALTH_APPLY,
            actor_user_id=current_user.id,
            actor_username=current_user.username,
            entity_type="wazuh_manager_rules",
            entity_id=RULES_FILENAME,
            result=AuditResult.FAILURE if step.status == "failed" else AuditResult.SUCCESS,
            new_value={"step": step.status, "detail": step.detail, "assets": asset_version()},
            request=request,
        )

    async def audit_group(item: SysmonHealthApplyResult) -> None:
        # One row per group, written as each group completes, so a failure part way through keeps the record.
        await record_audit_event(
            action=AuditAction.SYSMON_HEALTH_APPLY,
            actor_user_id=current_user.id,
            actor_username=current_user.username,
            customer_code=item.customer_code,
            entity_type="wazuh_group",
            entity_id=item.group,
            result=AuditResult.SUCCESS if item.success else AuditResult.FAILURE,
            new_value=_audit_payload(item, install_rules),
            request=request,
        )

    return await apply_sysmon_health_all(
        session,
        dry_run=dry_run,
        install_rules_if_needed=install_rules,
        on_rules_step=None if dry_run else audit_rules_step,
        on_result=None if dry_run else audit_group,
    )


@sysmon_health_router.get(
    "/{customer_code}",
    response_model=SysmonHealthStatus,
    dependencies=[Security(AuthHandler().require_any_scope("admin")), Depends(verify_customer_code_access)],
)
async def get_customer_sysmon_health(customer_code: str, session: AsyncSession = Depends(get_db)):
    """Where this customer's Windows group stands: rules, shared scripts, sysmon_config.xml and agent.conf wodles."""
    return await get_sysmon_health_status(customer_code, session)


@sysmon_health_router.post(
    "/{customer_code}/apply",
    response_model=SysmonHealthApplyResult,
    dependencies=[Security(AuthHandler().require_any_scope("admin")), Depends(verify_customer_code_access)],
)
async def apply_customer_sysmon_health(
    customer_code: str,
    request: Request,
    dry_run: bool = Query(True, description=DRY_RUN_HELP),
    install_rules: bool = Query(False, description=INSTALL_RULES_HELP),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Bring this customer's Windows group up to date, in order: rules, shared scripts, then agent.conf."""
    result = await apply_sysmon_health(customer_code, session, dry_run=dry_run, install_rules_if_needed=install_rules)
    if not dry_run:
        await record_audit_event(
            action=AuditAction.SYSMON_HEALTH_APPLY,
            actor_user_id=current_user.id,
            actor_username=current_user.username,
            customer_code=customer_code,
            entity_type="wazuh_group",
            entity_id=result.group,
            result=AuditResult.SUCCESS if result.success else AuditResult.FAILURE,
            new_value=_audit_payload(result, install_rules),
            request=request,
        )
    return result
