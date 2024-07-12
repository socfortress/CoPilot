from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.schema.pipelines import CreatePipeline
from app.connectors.graylog.schema.pipelines import CreatePipelineRule
from app.connectors.graylog.schema.pipelines import GraylogPipelinesResponse
from app.connectors.graylog.schema.pipelines import ModifyPipeline
from app.connectors.graylog.schema.pipelines import Pipeline
from app.connectors.graylog.schema.pipelines import PipelineRule
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request
from app.connectors.graylog.utils.universal import send_put_request
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineRequest
from app.customer_provisioning.schema.graylog import StreamConnectionToPipelineResponse


async def get_pipelines() -> GraylogPipelinesResponse:
    """Get pipelines from Graylog.

    Returns:
        GraylogPipelinesResponse: The response object containing the collected pipelines.

    Raises:
        HTTPException: If there is an error collecting the pipelines.
    """
    logger.info("Getting pipelines from Graylog")
    pipelines_collected = await send_get_request(
        endpoint="/api/system/pipelines/pipeline",
    )
    try:
        if pipelines_collected["success"]:
            pipelines_list = [Pipeline(**pipeline_data) for pipeline_data in pipelines_collected["data"]]
            return GraylogPipelinesResponse(
                pipelines=pipelines_list,
                success=True,
                message="Pipelines collected successfully",
            )
    except KeyError as e:
        logger.error(f"Failed to collect pipelines key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect pipelines key: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to collect pipelines: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect pipelines: {e}")


async def get_pipeline_rules() -> PipelineRulesResponse:
    """
    Get pipeline rules from Graylog.

    Returns:
        PipelineRulesResponse: The response object containing the pipeline rules.
    """
    logger.info("Getting pipeline rules from Graylog")
    pipeline_rules_collected = await send_get_request(
        endpoint="/api/system/pipelines/rule",
    )
    try:
        if pipeline_rules_collected["success"]:
            pipeline_rules_list = [PipelineRule(**pipeline_rule_data) for pipeline_rule_data in pipeline_rules_collected["data"]]
            return PipelineRulesResponse(
                pipeline_rules=pipeline_rules_list,
                success=True,
                message="Pipeline rules collected successfully",
            )
    except KeyError as e:
        logger.error(f"Failed to collect pipeline rules key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect pipeline rules key: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to collect pipeline rules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect pipeline rules: {e}",
        )


async def get_pipeline_rule_by_id(rule_id) -> PipelineRulesResponse:
    """
    Get pipeline rules from Graylog by ID.

    Args:
        rule_id (str): The ID of the pipeline rule.

    Returns:
        PipelineRulesResponse: The response containing the pipeline rule.

    Raises:
        HTTPException: If there is an error collecting the pipeline rules.
    """
    logger.info(f"Getting pipeline rules from Graylog for pipeline {rule_id}")
    pipeline_rules_collected = await send_get_request(
        endpoint=f"/api/system/pipelines/rule/{rule_id}",
    )
    logger.info(pipeline_rules_collected)
    try:
        if pipeline_rules_collected["success"]:
            pipeline_rule = PipelineRule(**pipeline_rules_collected["data"])
            return PipelineRulesResponse(
                pipeline_rules=[pipeline_rule],
                success=True,
                message="Pipeline rules collected successfully",
            )
    except KeyError as e:
        logger.error(f"Failed to collect pipeline rules key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect pipeline rules key: {e}",
        )
    except Exception as e:
        logger.error(f"Failed to collect pipeline rules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect pipeline rules: {e}",
        )


async def create_pipeline_rule(rule: CreatePipelineRule) -> None:
    """
    Creates a pipeline rule with the given title.
    """
    endpoint = "/api/system/pipelines/rule"
    data = {
        "title": rule.title,
        "description": rule.description,
        "source": rule.source,
    }
    await send_post_request(endpoint=endpoint, data=data)


async def create_pipeline_graylog(pipeline: CreatePipeline) -> None:
    """
    Creates a pipeline with the given title in Graylog.
    """
    endpoint = "/api/system/pipelines/pipeline"
    data = {
        "title": pipeline.title,
        "description": pipeline.description,
        "source": pipeline.source,
    }
    await send_post_request(endpoint=endpoint, data=data)


async def modify_pipeline_graylog(pipeline: ModifyPipeline) -> None:
    """
    Modifies a pipeline with the given title in Graylog.
    """
    endpoint = f"/api/system/pipelines/pipeline/{pipeline.pipeline_id}"
    data = {
        "source": pipeline.source,
    }
    await send_put_request(endpoint=endpoint, data=data)


async def get_pipeline_id(subscription: str) -> str:
    """
    Retrieves the pipeline ID for a given subscription.

    Args:
        subscription (str): The subscription name.

    Returns:
        str: The pipeline ID.

    Raises:
        HTTPException: If the pipeline ID cannot be retrieved.
    """
    logger.info(f"Getting pipeline ID for subscription {subscription}")
    pipelines_response = await get_pipelines()
    if pipelines_response.success:
        for pipeline in pipelines_response.pipelines:
            if subscription.lower() in pipeline.description.lower():
                return [pipeline.id]
        logger.error(f"Failed to get pipeline ID for subscription {subscription}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline ID for subscription {subscription}",
        )
    else:
        logger.error(f"Failed to get pipelines: {pipelines_response.message}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipelines: {pipelines_response.message}",
        )


async def connect_stream_to_pipeline(
    stream_and_pipeline: StreamConnectionToPipelineRequest,
):
    """
    Connects a stream to a pipeline.

    Args:
        stream_and_pipeline (StreamConnectionToPipelineRequest): The request object containing the stream ID and pipeline IDs.

    Returns:
        StreamConnectionToPipelineResponse: The response object containing the connection details.
    """
    logger.info(
        f"Connecting stream {stream_and_pipeline.stream_id} to pipeline {stream_and_pipeline.pipeline_ids}",
    )
    response_json = await send_post_request(
        endpoint="/api/system/pipelines/connections/to_stream",
        data=stream_and_pipeline.dict(),
    )
    logger.info(f"Response: {response_json}")
    return StreamConnectionToPipelineResponse(**response_json)
