from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger
from pydantic import Field

from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.connectors.graylog.schema.pipelines import Pipeline
from app.connectors.graylog.schema.pipelines import PipelineRule
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.schema.pipelines import Stage
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request


def get_pipelines() -> GraylogPipelinesResponse:
    """Get pipelines from Graylog."""
    logger.info(f"Getting pipelines from Graylog")
    pipelines_collected = send_get_request(endpoint="/api/system/pipelines/pipeline")
    if pipelines_collected["success"]:
        pipelines_list = [Pipeline(**pipeline_data) for pipeline_data in pipelines_collected["data"]]
        return GraylogPipelinesResponse(pipelines=pipelines_list, success=True, message="Pipelines collected successfully")
    else:
        return GraylogPipelinesResponse(pipelines=[], success=False, message="Failed to collect pipelines")


def get_pipeline_rules() -> PipelineRulesResponse:
    """Get pipeline rules from Graylog."""
    logger.info(f"Getting pipeline rules from Graylog")
    pipeline_rules_collected = send_get_request(endpoint="/api/system/pipelines/rule")
    if pipeline_rules_collected["success"]:
        pipeline_rules_list = [PipelineRule(**pipeline_rule_data) for pipeline_rule_data in pipeline_rules_collected["data"]]
        return PipelineRulesResponse(pipeline_rules=pipeline_rules_list, success=True, message="Pipeline rules collected successfully")
    else:
        return PipelineRulesResponse(pipeline_rules=[], success=False, message="Failed to collect pipeline rules")
