from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.connectors.graylog.schema.pipelines import Pipeline
from app.connectors.graylog.schema.pipelines import PipelineRule
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.utils.universal import send_get_request


def get_pipelines() -> GraylogPipelinesResponse:
    """Get pipelines from Graylog."""
    logger.info("Getting pipelines from Graylog")
    pipelines_collected = send_get_request(endpoint="/api/system/pipelines/pipeline")
    try:
        if pipelines_collected["success"]:
            pipelines_list = [Pipeline(**pipeline_data) for pipeline_data in pipelines_collected["data"]]
            return GraylogPipelinesResponse(pipelines=pipelines_list, success=True, message="Pipelines collected successfully")
    except KeyError as e:
        logger.error(f"Failed to collect pipelines key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipelines key: {e}")
    except Exception as e:
        logger.error(f"Failed to collect pipelines: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipelines: {e}")


def get_pipeline_rules() -> PipelineRulesResponse:
    """Get pipeline rules from Graylog."""
    logger.info("Getting pipeline rules from Graylog")
    pipeline_rules_collected = send_get_request(endpoint="/api/system/pipelines/rule")
    try:
        if pipeline_rules_collected["success"]:
            pipeline_rules_list = [PipelineRule(**pipeline_rule_data) for pipeline_rule_data in pipeline_rules_collected["data"]]
            return PipelineRulesResponse(pipeline_rules=pipeline_rules_list, success=True, message="Pipeline rules collected successfully")
    except KeyError as e:
        logger.error(f"Failed to collect pipeline rules key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipeline rules key: {e}")
    except Exception as e:
        logger.error(f"Failed to collect pipeline rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipeline rules: {e}")


def get_pipeline_rule_by_id(pipeline_id) -> PipelineRulesResponse:
    """Get pipeline rules from Graylog."""
    logger.info(f"Getting pipeline rules from Graylog for pipeline {pipeline_id}")
    pipeline_rules_collected = send_get_request(endpoint=f"/api/system/pipelines/rule/{pipeline_id}")
    logger.info(pipeline_rules_collected)
    try:
        if pipeline_rules_collected["success"]:
            pipeline_rule = PipelineRule(**pipeline_rules_collected["data"])
            return PipelineRulesResponse(pipeline_rules=[pipeline_rule], success=True, message="Pipeline rules collected successfully")
    except KeyError as e:
        logger.error(f"Failed to collect pipeline rules key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipeline rules key: {e}")
    except Exception as e:
        logger.error(f"Failed to collect pipeline rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipeline rules: {e}")
