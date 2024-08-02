import json

from loguru import logger
from sigma.collection import SigmaCollection
from sigma.processing.resolver import ProcessingPipelineResolver

from app.connectors.wazuh_indexer.schema.sigma import SigmaQueryGenerationResponse
from app.connectors.wazuh_indexer.services.sigma.opensearch import (
    OpensearchLuceneBackend,
)
from app.connectors.wazuh_indexer.services.sigma.sysmon import sysmon_pipeline
from app.connectors.wazuh_indexer.services.sigma.windows import ecs_windows


async def create_sigma_query_from_rule(rule: str) -> SigmaQueryGenerationResponse:
    # Create our pipeline resolver
    piperesolver = ProcessingPipelineResolver()

    # Add wanted pipelines
    piperesolver.add_pipeline_class(ecs_windows())
    piperesolver.add_pipeline_class(sysmon_pipeline())

    # Create a single sorted and prioritzed pipeline
    resolved_pipeline = piperesolver.resolve(piperesolver.pipelines)

    # Instantiate backend, using our resolved pipeline
    # and some backend parameter
    backend = OpensearchLuceneBackend(
        resolved_pipeline, index_names=["logs-*-*", "beats-*"], monitor_interval=10, monitor_interval_unit="MINUTES",
    )

    rules = SigmaCollection.from_yaml(rule)

    # Convert the rule to DSL format
    dsl_result = backend.convert(rules, output_format="dsl_lucene")[0]

    # Create the Pydantic model from the DSL result
    sigma_query_out_response = SigmaQueryGenerationResponse.parse_obj(dsl_result)

    # return the DSL query as a string
    return sigma_query_out_response
