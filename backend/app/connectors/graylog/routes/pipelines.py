from fastapi import APIRouter
from fastapi import Security
from loguru import logger
from typing import Dict

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse, GraylogPipelinesResponseWithRuleID, PipelineWithRuleID, StageWithRuleID
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.services.pipelines import get_pipeline_rule_by_id
from app.connectors.graylog.services.pipelines import get_pipeline_rules
from app.connectors.graylog.services.pipelines import get_pipelines

# App specific imports


graylog_pipelines_router = APIRouter()


@graylog_pipelines_router.get(
    "/pipelines",
    response_model=GraylogPipelinesResponse,
    description="Get all pipelines",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipelines() -> GraylogPipelinesResponse:
    logger.info("Fetching all graylog pipelines")
    return get_pipelines()

@graylog_pipelines_router.get(
    "/pipeline/full",
    response_model=GraylogPipelinesResponseWithRuleID,  # Use the new response model
    description="Get all pipelines with rule IDs",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipelines_with_rule_ids() -> GraylogPipelinesResponseWithRuleID:
    # Fetch all pipelines
    pipelines_response = get_pipelines()
    # Fetch all pipeline rules
    pipeline_rules_response = get_pipeline_rules()

    # Create a lookup dict for rule titles to IDs
    rule_title_to_id: Dict[str, str] = {}
    for rule in pipeline_rules_response.pipeline_rules:
        rule_title_to_id[rule.title] = rule.id

    # Convert existing pipelines to the new format
    new_pipelines = []
    for pipeline in pipelines_response.pipelines:
        new_stages = []
        for stage in pipeline.stages:
            rule_ids = [rule_title_to_id.get(rule_title, None) for rule_title in stage.rules]
            new_stage = StageWithRuleID(**stage.dict(), rule_ids=rule_ids)
            new_stages.append(new_stage)

        pipeline_dict = pipeline.dict()
        pipeline_dict['stages'] = new_stages
        new_pipeline = PipelineWithRuleID(**pipeline_dict)
        new_pipelines.append(new_pipeline)

    # Return the updated response
    return GraylogPipelinesResponseWithRuleID(
        pipelines=new_pipelines,
        success=pipelines_response.success,
        message=pipelines_response.message
    )




@graylog_pipelines_router.get(
    "/pipeline/rules",
    response_model=PipelineRulesResponse,
    description="Get all pipeline rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipeline_rules() -> PipelineRulesResponse:
    logger.info("Fetching all graylog pipeline rules")
    return get_pipeline_rules()


@graylog_pipelines_router.get(
    "/pipeline/rules/{pipeline_id}",
    response_model=PipelineRulesResponse,
    description="Get all pipeline rules for a pipeline",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_pipeline_rules_for_pipeline(pipeline_id: str) -> PipelineRulesResponse:
    logger.info(f"Fetching all graylog pipeline rules for pipeline {pipeline_id}")
    return get_pipeline_rule_by_id(pipeline_id)
