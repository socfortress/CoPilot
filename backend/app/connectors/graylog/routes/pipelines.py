from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
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
    "/pipeline/rules",
    response_model=PipelineRulesResponse,
    description="Get all pipeline rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_pipeline_rules() -> PipelineRulesResponse:
    logger.info("Fetching all graylog pipeline rules")
    return get_pipeline_rules()
