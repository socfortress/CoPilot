from fastapi import APIRouter
from fastapi import Security
from loguru import logger
from typing import Dict, List

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse, GraylogPipelinesResponseWithRuleID, PipelineWithRuleID, StageWithRuleID, Stage, Pipeline, PipelineRule
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.services.pipelines import get_pipeline_rule_by_id
from app.connectors.graylog.services.pipelines import get_pipeline_rules
from app.connectors.graylog.services.pipelines import get_pipelines

# App specific imports


graylog_pipelines_router = APIRouter()

def create_rule_title_to_id_dict(pipeline_rules: List[PipelineRule]) -> Dict[str, str]:
    rule_title_to_id = {}
    for rule in pipeline_rules:
        rule_title_to_id[rule.title] = rule.id
    return rule_title_to_id

def transform_stages_with_rule_ids(stages: List[Stage], rule_title_to_id: Dict[str, str]) -> List[StageWithRuleID]:
    new_stages = []
    for stage in stages:
        rule_ids = [rule_title_to_id.get(rule_title, None) for rule_title in stage.rules]
        new_stage = StageWithRuleID(**stage.dict(), rule_ids=rule_ids)
        new_stages.append(new_stage)
    return new_stages

def transform_pipeline_with_rule_ids(pipeline: Pipeline, rule_title_to_id: Dict[str, str]) -> PipelineWithRuleID:
    new_stages = transform_stages_with_rule_ids(pipeline.stages, rule_title_to_id)
    pipeline_dict = pipeline.dict()
    pipeline_dict['stages'] = new_stages
    return PipelineWithRuleID(**pipeline_dict)

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
    response_model=GraylogPipelinesResponseWithRuleID,
    description="Get all pipelines with rule IDs",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipelines_with_rule_ids() -> GraylogPipelinesResponseWithRuleID:
    pipelines_response = get_pipelines()
    pipeline_rules_response = get_pipeline_rules()

    rule_title_to_id = create_rule_title_to_id_dict(pipeline_rules_response.pipeline_rules)

    new_pipelines = [transform_pipeline_with_rule_ids(pipeline, rule_title_to_id) for pipeline in pipelines_response.pipelines]

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
