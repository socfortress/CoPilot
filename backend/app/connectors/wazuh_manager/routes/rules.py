from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# App specific imports
from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.models.rules import DisabledRule
from app.connectors.wazuh_manager.schema.rules import AllDisabledRuleResponse
from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse
from app.connectors.wazuh_manager.schema.rules import RuleExclude
from app.connectors.wazuh_manager.schema.rules import RuleExcludeResponse
from app.connectors.wazuh_manager.services.rules import disable_rule
from app.connectors.wazuh_manager.services.rules import enable_rule
from app.connectors.wazuh_manager.services.rules import exclude_rule
from app.db.db_session import get_session, get_db

NEW_LEVEL = "1"
wazuh_manager_rules_router = APIRouter()
auth_handler = AuthHandler()


def query_disabled_rule(rule_id: str):
    return session.query(DisabledRule).filter(DisabledRule.rule_id == rule_id).first()


@wazuh_manager_rules_router.get(
    "/rule/disabled",
    response_model=AllDisabledRuleResponse,
    description="Get all disabled rules",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_disabled_rules(session: AsyncSession = Depends(get_db)) -> AllDisabledRuleResponse:
    result = await session.execute(select(DisabledRule))
    disabled_rules = result.scalars().all()
    return AllDisabledRuleResponse(disabled_rules=disabled_rules, success=True, message="Successfully fetched all disabled rules")


# @wazuh_manager_rules_router.post(
#     "/rule/disable",
#     response_model=RuleDisableResponse,
#     description="Disable a Wazuh Rule",
#     dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
# )
# async def disable_wazuh_rule(rule: RuleDisable, username: str = Depends(auth_handler.get_current_user)) -> RuleDisableResponse:
#     if query_disabled_rule(rule.rule_id):
#         raise HTTPException(status_code=500, detail="Rule is already disabled")

#     rule_disabled = disable_rule(rule)
#     if rule_disabled:
#         new_disabled_rule = DisabledRule(
#             rule_id=rule.rule_id,
#             previous_level=rule_disabled.previous_level,
#             new_level=NEW_LEVEL,
#             reason_for_disabling=rule.reason_for_disabling,
#             length_of_time=rule.length_of_time,
#             disabled_by=username.username,
#         )
#         session.add(new_disabled_rule)
#         session.commit()
#         return rule_disabled
#     else:
#         raise HTTPException(status_code=404, detail="Was not able to disable rule")


@wazuh_manager_rules_router.post(
    "/rule/disable",
    response_model=RuleDisableResponse,
    description="Disable a Wazuh Rule",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def disable_wazuh_rule(
    rule: RuleDisable,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(AuthHandler().get_current_user),
) -> RuleDisableResponse:
    # Asynchronously check if the rule is already disabled
    result = await session.execute(select(DisabledRule).where(DisabledRule.rule_id == rule.rule_id))
    if result.scalars().first():
        raise HTTPException(status_code=500, detail="Rule is already disabled")

    # This should be converted to an async operation if it's not already
    rule_disabled = await disable_rule(rule)
    if rule_disabled:
        new_disabled_rule = DisabledRule(
            rule_id=rule.rule_id,
            previous_level=rule_disabled.previous_level,
            new_level=NEW_LEVEL,
            reason_for_disabling=rule.reason_for_disabling,
            length_of_time=rule.length_of_time,
            disabled_by=username.username,
        )
        session.add(new_disabled_rule)
        await session.commit()
        return rule_disabled
    else:
        raise HTTPException(status_code=404, detail="Was not able to disable rule")


# @wazuh_manager_rules_router.post(
#     "/rule/enable",
#     response_model=RuleEnableResponse,
#     description="Enable a Wazuh Rule",
#     dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
# )
# async def enable_wazuh_rule(rule: RuleEnable) -> RuleEnableResponse:
#     disabled_rule = query_disabled_rule(rule.rule_id)
#     if not disabled_rule:
#         raise HTTPException(status_code=404, detail="Rule is already enabled")

#     previous_level = disabled_rule.previous_level
#     rule_enabled = enable_rule(rule, previous_level)

#     if rule_enabled:
#         session.delete(disabled_rule)
#         session.commit()
#         return rule_enabled
#     else:
#         raise HTTPException(status_code=404, detail="Was not able to enable rule")


@wazuh_manager_rules_router.post(
    "/rule/enable",
    response_model=RuleEnableResponse,
    description="Enable a Wazuh Rule",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def enable_wazuh_rule(rule: RuleEnable, session: AsyncSession = Depends(get_db)) -> RuleEnableResponse:
    # Asynchronously fetch the disabled rule
    logger.info(f"rule: {rule}")
    result = await session.execute(select(DisabledRule).where(DisabledRule.rule_id == rule.rule_id))
    disabled_rule = result.scalars().first()

    if not disabled_rule:
        raise HTTPException(status_code=404, detail="Rule is already enabled")

    # This should be converted to an async operation if it's not already
    rule_enabled = await enable_rule(rule, disabled_rule.previous_level)

    if rule_enabled:
        await session.delete(disabled_rule)
        await session.commit()
        return rule_enabled
    else:
        raise HTTPException(status_code=404, detail="Was not able to enable rule")


# ! TODO: Implement this endpoint
# @wazuh_manager_router.post(
#     "/rule/exclude",
#     response_model=RuleExcludeResponse,
#     description="Retrieve recommended exclusion for a Wazuh Rule",
# )
# async def exclude_wazuh_rule(rule: RuleExclude) -> RuleExcludeResponse:
#     recommended_exclusion = exclude_rule(rule)
#     if recommended_exclusion:
#         return recommended_exclusion
#     else:
#         raise HTTPException(status_code=404, detail="Was not able to exclude rule")
