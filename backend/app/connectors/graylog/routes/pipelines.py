from typing import Dict
from typing import List

from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponseWithRuleID
from app.connectors.graylog.schema.pipelines import Pipeline
from app.connectors.graylog.schema.pipelines import PipelineRule
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.schema.pipelines import PipelineWithRuleID
from app.connectors.graylog.schema.pipelines import Stage
from app.connectors.graylog.schema.pipelines import StageWithRuleID
from app.connectors.graylog.services.pipelines import get_pipeline_rule_by_id
from app.connectors.graylog.services.pipelines import get_pipeline_rules
from app.connectors.graylog.services.pipelines import get_pipelines

# App specific imports


graylog_pipelines_router = APIRouter()


def create_rule_title_to_id_dict(pipeline_rules: List[PipelineRule]) -> Dict[str, str]:
    """
    Creates a dictionary mapping rule titles to rule IDs.

    Args:
        pipeline_rules (List[PipelineRule]): List of pipeline rules.

    Returns:
        Dict[str, str]: Dictionary mapping rule titles to rule IDs.
    """
    rule_title_to_id = {}
    for rule in pipeline_rules:
        rule_title_to_id[rule.title] = rule.id
    return rule_title_to_id


def transform_stages_with_rule_ids(
    stages: List[Stage],
    rule_title_to_id: Dict[str, str],
) -> List[StageWithRuleID]:
    """
    Transforms a list of stages by adding corresponding rule IDs based on a dictionary mapping rule titles to IDs.

    Args:
        stages (List[Stage]): The list of stages to transform.
        rule_title_to_id (Dict[str, str]): The dictionary mapping rule titles to IDs.

    Returns:
        List[StageWithRuleID]: The transformed list of stages with added rule IDs.
    """
    new_stages = []
    for stage in stages:
        rule_ids = [rule_title_to_id.get(rule_title, None) for rule_title in stage.rules]
        new_stage = StageWithRuleID(**stage.dict(), rule_ids=rule_ids)
        new_stages.append(new_stage)
    return new_stages


def transform_pipeline_with_rule_ids(
    pipeline: Pipeline,
    rule_title_to_id: Dict[str, str],
) -> PipelineWithRuleID:
    """
    Transforms a pipeline by replacing rule titles with rule IDs.

    Args:
        pipeline (Pipeline): The original pipeline object.
        rule_title_to_id (Dict[str, str]): A dictionary mapping rule titles to rule IDs.

    Returns:
        PipelineWithRuleID: The transformed pipeline object with rule IDs.

    """
    new_stages = transform_stages_with_rule_ids(pipeline.stages, rule_title_to_id)
    pipeline_dict = pipeline.dict()
    pipeline_dict["stages"] = new_stages
    return PipelineWithRuleID(**pipeline_dict)


@graylog_pipelines_router.get(
    "/pipelines",
    response_model=GraylogPipelinesResponse,
    description="Get all pipelines",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipelines() -> GraylogPipelinesResponse:
    """
    Get all pipelines.

    Returns:
        GraylogPipelinesResponse: The response model containing the pipelines.
    """
    logger.info("Fetching all graylog pipelines")
    return await get_pipelines()


@graylog_pipelines_router.get(
    "/pipeline/full",
    response_model=GraylogPipelinesResponseWithRuleID,
    description="Get all pipelines with rule IDs",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipelines_with_rule_ids() -> GraylogPipelinesResponseWithRuleID:
    """
    Retrieve all pipelines with their associated rule IDs.

    Returns:
        GraylogPipelinesResponseWithRuleID: The response containing the pipelines with rule IDs.
    """
    pipelines_response = await get_pipelines()
    pipeline_rules_response = await get_pipeline_rules()

    rule_title_to_id = create_rule_title_to_id_dict(
        pipeline_rules_response.pipeline_rules,
    )

    new_pipelines = [transform_pipeline_with_rule_ids(pipeline, rule_title_to_id) for pipeline in pipelines_response.pipelines]

    return GraylogPipelinesResponseWithRuleID(
        pipelines=new_pipelines,
        success=pipelines_response.success,
        message=pipelines_response.message,
    )


@graylog_pipelines_router.get(
    "/pipeline/rules",
    response_model=PipelineRulesResponse,
    description="Get all pipeline rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipeline_rules() -> PipelineRulesResponse:
    """
    Fetches all graylog pipeline rules.

    Returns:
        PipelineRulesResponse: The response containing all pipeline rules.
    """
    logger.info("Fetching all graylog pipeline rules")
    return await get_pipeline_rules()


@graylog_pipelines_router.get(
    "/pipeline/rules/{pipeline_id}",
    response_model=PipelineRulesResponse,
    description="Get all pipeline rules for a pipeline",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_pipeline_rules_for_pipeline(pipeline_id: str) -> PipelineRulesResponse:
    """
    Get all pipeline rules for a specific pipeline.

    Args:
        pipeline_id (str): The ID of the pipeline.

    Returns:
        PipelineRulesResponse: The response containing the pipeline rules.
    """
    logger.info(f"Fetching all graylog pipeline rules for pipeline {pipeline_id}")
    return await get_pipeline_rule_by_id(pipeline_id)
