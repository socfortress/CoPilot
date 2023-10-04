from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session
from app.connectors.graylog.schema.pipelines import (
    GraylogPipelinesResponse, PipelineRulesResponse
)
from app.connectors.graylog.services.pipelines import get_pipelines, get_pipeline_rules

graylog_pipelines_router = APIRouter()


@graylog_pipelines_router.get("/pipelines", response_model=GraylogPipelinesResponse, description="Get all pipelines")
async def get_all_pipelines() -> GraylogPipelinesResponse:
    logger.info(f"Fetching all graylog pipelines")
    return get_pipelines()

@graylog_pipelines_router.get("/pipeline/rules", response_model=PipelineRulesResponse, description="Get all pipeline rules")
async def get_all_pipeline_rules() -> PipelineRulesResponse:
    logger.info(f"Fetching all graylog pipeline rules")
    return get_pipeline_rules()