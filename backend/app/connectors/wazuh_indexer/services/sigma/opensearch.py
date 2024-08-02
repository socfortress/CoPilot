from typing import ClassVar
from typing import Dict
from typing import List
from typing import Optional

import sigma
from sigma.conversion.state import ConversionState
from sigma.rule import SigmaRule

from app.connectors.wazuh_indexer.services.sigma.elasticsearch import LuceneBackend


class OpensearchLuceneBackend(LuceneBackend):
    """OpensearchLuceneBackend backend."""

    name: ClassVar[str] = "OpenSearch Lucene"  # A descriptive name of the backend
    formats: ClassVar[
        Dict[str, str]
    ] = {  # Output formats provided by the backend as name -> description mapping. The name should match to finalize_output_<name>.
        "default": "Plain OpenSearch Lucene queries",
        "dashboards_ndjson": "OpenSearch Dashboards NDJSON import file with Lucene queries",
        "monitor_rule": "OpenSearch monitor rule with embedded Lucene query",
        "dsl_lucene": "OpenSearch query DSL with embedded Lucene queries",
    }
    # Does the backend requires that a processing pipeline is provided?
    requires_pipeline: ClassVar[bool] = True

    def __init__(
        self,
        processing_pipeline: Optional["sigma.processing.pipeline.ProcessingPipeline"] = None,
        collect_errors: bool = False,
        index_names: List = ["beats-*"],
        monitor_interval: int = 5,
        monitor_interval_unit: str = "MINUTES",
        **kwargs,
    ):
        super().__init__(processing_pipeline, collect_errors, **kwargs)
        self.index_names = index_names or ["beats-*"]
        self.monitor_interval = monitor_interval or 5
        self.monitor_interval_unit = monitor_interval_unit or "MINUTES"

    def finalize_query_monitor_rule(self, rule: SigmaRule, query: str, index: int, state: ConversionState) -> dict:
        severity_mapping = {5: 1, 4: 2, 3: 3, 2: 4, 1: 5}
        monitor_rule = {
            "type": "monitor",
            "name": f"SIGMA - {rule.title}",
            "description": rule.description,
            "enabled": True,
            "schedule": {"period": {"interval": self.monitor_interval, "unit": self.monitor_interval_unit}},
            "inputs": [
                {
                    "search": {
                        "indices": self.index_names,
                        "query": {"size": 1, "query": {"bool": {"must": [{"query_string": {"query": query, "analyze_wildcard": True}}]}}},
                    },
                },
            ],
            "tags": [f"{n.namespace}-{n.name}" for n in rule.tags],
            "triggers": [
                {
                    "name": "generated-trigger",
                    "severity": severity_mapping[rule.level.value] if rule.level is not None else 1,
                    "condition": {"script": {"source": "ctx.results[0].hits.total.value > 0", "lang": "painless"}},
                    "actions": [],
                },
            ],
            "sigma_meta_data": {"rule_id": str(rule.id), "threat": []},
            "references": rule.references,
        }

        return monitor_rule

    def finalize_output_monitor_rule(self, queries: List[str]) -> str:
        return list(queries)

    def finalize_query_dashboards_ndjson(self, rule: SigmaRule, query: str, index: int, state: ConversionState) -> str:
        """Alias to Kibana NDJSON query finalization."""
        return self.finalize_query_kibana_ndjson(rule, query, index, state)

    def finalize_output_dashboards_ndjson(self, queries: List[str]) -> str:
        """Alias to Kibana NDJSON output finalization."""
        return self.finalize_output_kibana_ndjson(queries)
