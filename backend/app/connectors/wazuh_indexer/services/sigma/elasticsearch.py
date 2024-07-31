import re
import json
from typing import Iterable, ClassVar, Dict, List, Optional, Pattern, Tuple, Union, Any

from sigma.conversion.state import ConversionState
from sigma.rule import SigmaRule, SigmaRuleTag
from sigma.conversion.base import TextQueryBackend
from sigma.conversion.deferred import DeferredQueryExpression
from sigma.conditions import (
    ConditionItem,
    ConditionAND,
    ConditionOR,
    ConditionNOT,
    ConditionFieldEqualsValueExpression,
)
from sigma.types import SigmaCompareExpression, SigmaNull
from sigma.data.mitre_attack import mitre_attack_tactics, mitre_attack_techniques
import sigma


class LuceneBackend(TextQueryBackend):
    """
    Elasticsearch query string backend. Generates query strings described here in the
    Elasticsearch documentation:

    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#query-string-syntax
    """

    # A descriptive name of the backend
    name: ClassVar[str] = "Elasticsearch Lucene"
    # Output formats provided by the backend as name -> description mapping.
    # The name should match to finalize_output_<name>.
    formats: ClassVar[Dict[str, str]] = {
        "default": "Plain Elasticsearch Lucene queries",
        "kibana_ndjson": "Kibana NDJSON import file with Lucene queries",
        "dsl_lucene": "Elasticsearch query DSL with embedded Lucene queries",
        "siem_rule": "Elasticsearch query DSL as SIEM Rules in JSON Format",
        "siem_rule_ndjson": "Elasticsearch query DSL as SIEM Rules in NDJSON Format",
    }
    # Does the backend requires that a processing pipeline is provided?
    requires_pipeline: ClassVar[bool] = True

    # Operator precedence: tuple of Condition{AND,OR,NOT} in order of precedence.
    # The backend generates grouping if required
    precedence: ClassVar[Tuple[ConditionItem, ConditionItem, ConditionItem]] = (
        ConditionNOT,
        ConditionOR,
        ConditionAND,
    )
    # Expression for precedence override grouping as format string with {expr} placeholder
    group_expression: ClassVar[str] = "({expr})"
    parenthesize: bool = True

    # Generated query tokens
    token_separator: str = " "  # separator inserted between all boolean operators
    or_token: ClassVar[str] = "OR"
    and_token: ClassVar[str] = "AND"
    not_token: ClassVar[str] = "NOT"
    # Token inserted between field and value (without separator)
    eq_token: ClassVar[str] = ":"

    # String output
    # Fields
    # No quoting of field names
    # Escaping
    # Character to escape particular parts defined in field_escape_pattern.
    field_escape: ClassVar[str] = "\\"
    # All matches of this pattern are prepended with the string contained in field_escape.
    field_escape_pattern: ClassVar[Pattern] = re.compile("[\\s*]")

    # Values
    # string quoting character (added as escaping character)
    str_quote: ClassVar[str] = '"'
    str_quote_pattern: ClassVar[Pattern] = re.compile(r"^$")
    str_quote_pattern_negation: ClassVar[bool] = False
    # Escaping character for special characrers inside string
    escape_char: ClassVar[str] = "\\"
    # Character used as multi-character wildcard
    wildcard_multi: ClassVar[str] = "*"
    # Character used as single-character wildcard
    wildcard_single: ClassVar[str] = "?"
    # Characters quoted in addition to wildcards and string quote
    add_escaped: ClassVar[str] = '+-=&|!(){}[]<>^"~*?:\\/ '
    bool_values: ClassVar[Dict[bool, str]] = (
        {  # Values to which boolean values are mapped.
            True: "true",
            False: "false",
        }
    )

    # Regular expressions
    # Regular expression query as format string with placeholders {field} and {regex}
    re_expression: ClassVar[str] = "{field}:/{regex}/"
    # Character used for escaping in regular expressions
    re_escape_char: ClassVar[str] = "\\"
    re_escape: ClassVar[Tuple[str]] = ("/",)
    # Don't escape the escape char
    re_escape_escape_char: ClassVar[bool] = False

    # cidr expressions
    # CIDR expression query as format string with placeholders {field} = {value}
    cidr_expression: ClassVar[str] = "{field}:{network}\\/{prefixlen}"

    # Numeric comparison operators
    # Compare operation query as format string with placeholders {field}, {operator} and {value}
    compare_op_expression: ClassVar[str] = "{field}:{operator}{value}"
    # Mapping between CompareOperators elements and strings used as replacement
    # for {operator} in compare_op_expression
    compare_operators: ClassVar[Dict[SigmaCompareExpression.CompareOperators, str]] = {
        SigmaCompareExpression.CompareOperators.LT: "<",
        SigmaCompareExpression.CompareOperators.LTE: "<=",
        SigmaCompareExpression.CompareOperators.GT: ">",
        SigmaCompareExpression.CompareOperators.GTE: ">=",
    }

    # Null/None expressions
    # Expression for field has null value as format string with {field} placeholder for field name
    field_null_expression: ClassVar[str] = "NOT _exists_:{field}"

    # Field value in list, e.g. "field in (value list)" or "field containsall (value list)"
    # Convert OR as in-expression
    convert_or_as_in: ClassVar[bool] = True
    # Convert AND as in-expression
    convert_and_as_in: ClassVar[bool] = False
    # Values in list can contain wildcards. If set to False (default)
    # only plain values are converted into in-expressions.
    in_expressions_allow_wildcards: ClassVar[bool] = True
    # Expression for field in list of values as format string with
    # placeholders {field}, {op} and {list}
    field_in_list_expression: ClassVar[str] = "{field}{op}({list})"
    # Operator used to convert OR into in-expressions. Must be set if convert_or_as_in is set
    or_in_operator: ClassVar[str] = ":"
    # List element separator
    list_separator: ClassVar[str] = " OR "

    # Value not bound to a field
    # Expression for string value not bound to a field as format string with placeholder {value}
    unbound_value_str_expression: ClassVar[str] = "*{value}*"
    # Expression for number value not bound to a field as format string with placeholder {value}
    unbound_value_num_expression: ClassVar[str] = "{value}"

    def __init__(
        self,
        processing_pipeline: Optional[
            "sigma.processing.pipeline.ProcessingPipeline"
        ] = None,
        collect_errors: bool = False,
        index_names: List = [
            "apm-*-transaction*",
            "auditbeat-*",
            "endgame-*",
            "filebeat-*",
            "logs-*",
            "packetbeat-*",
            "traces-apm*",
            "winlogbeat-*",
            "-*elastic-cloud-logs-*",
        ],
        schedule_interval: int = 5,
        schedule_interval_unit: str = "m",
        **kwargs,
    ):
        super().__init__(processing_pipeline, collect_errors, **kwargs)
        self.index_names = index_names or [
            "apm-*-transaction*",
            "auditbeat-*",
            "endgame-*",
            "filebeat-*",
            "logs-*",
            "packetbeat-*",
            "traces-apm*",
            "winlogbeat-*",
            "-*elastic-cloud-logs-*",
        ]
        self.schedule_interval = schedule_interval or 5
        self.schedule_interval_unit = schedule_interval_unit or "m"
        self.severity_risk_mapping = {
            "INFORMATIONAL": 1,
            "LOW": 21,
            "MEDIUM": 47,
            "HIGH": 73,
            "CRITICAL": 99,
        }

    @staticmethod
    def _is_field_null_condition(cond: ConditionItem) -> bool:
        return isinstance(cond, ConditionFieldEqualsValueExpression) and isinstance(
            cond.value, SigmaNull
        )

    def convert_condition_not(
        self, cond: ConditionNOT, state: ConversionState
    ) -> Union[str, DeferredQueryExpression]:
        """When checking if a field is not null, convert "NOT NOT _exists_:field" to "_exists_:field"."""
        if LuceneBackend._is_field_null_condition(cond.args[0]):
            return f"_exists_:{cond.args[0].field}"

        return super().convert_condition_not(cond, state)

    def convert_condition_field_eq_val_cidr(
        self, cond: ConditionFieldEqualsValueExpression, state: ConversionState
    ) -> Union[str, DeferredQueryExpression]:
        if ":" in cond.value.cidr:
            return (
                super()
                .convert_condition_field_eq_val_cidr(cond, state)
                .replace(":", r"\:")
                .replace(r"\:", ":", 1)
            )
        else:
            return super().convert_condition_field_eq_val_cidr(cond, state)

    def convert_condition_field_eq_expansion(
        self, cond: ConditionFieldEqualsValueExpression, state: ConversionState
    ) -> Any:
        """
        Convert each value of the expansion with the field from the containing condition and OR-link
        all converted subconditions.
        """
        or_cond = ConditionOR(
            [
                ConditionFieldEqualsValueExpression(cond.field, value)
                for value in cond.value.values
            ],
            cond.source,
        )
        if self.decide_convert_condition_as_in_expression(or_cond, state):
            return self.convert_condition_as_in_expression(or_cond, state)
        else:
            return self.convert_condition_or(cond, state)

    def compare_precedence(self, outer: ConditionItem, inner: ConditionItem) -> bool:
        """Override precedence check for null field conditions."""
        if isinstance(inner, ConditionNOT) and LuceneBackend._is_field_null_condition(
            inner.args[0]
        ):
            # inner will turn into "_exists_:field", no parentheses needed
            return True

        if LuceneBackend._is_field_null_condition(inner):
            # inner will turn into "NOT _exists_:field", force parentheses
            return False

        return super().compare_precedence(outer, inner)

    def finalize_output_threat_model(self, tags: List[SigmaRuleTag]) -> Iterable[Dict]:
        attack_tags = [t for t in tags if t.namespace == "attack"]
        if not len(attack_tags) >= 2:
            return []

        techniques = [
            tag.name.upper() for tag in attack_tags if re.match(r"[tT]\d{4}", tag.name)
        ]
        tactics = [
            tag.name.lower()
            for tag in attack_tags
            if not re.match(r"[tT]\d{4}", tag.name)
        ]

        for tactic, technique in zip(tactics, techniques):
            if (
                not tactic or not technique
            ):  # Only add threat if tactic and technique is known
                continue

            try:
                if "." in technique:  # Contains reference to Mitre Att&ck subtechnique
                    sub_technique = technique
                    technique = technique[0:5]
                    sub_technique_name = mitre_attack_techniques[sub_technique]

                    sub_techniques = [
                        {
                            "id": sub_technique,
                            "reference": f"https://attack.mitre.org/techniques/{sub_technique.replace('.', '/')}",
                            "name": sub_technique_name,
                        }
                    ]
                else:
                    sub_techniques = []

                tactic_id = [
                    id
                    for (id, name) in mitre_attack_tactics.items()
                    if name == tactic.replace("_", "-")
                ][0]
                technique_name = mitre_attack_techniques[technique]
            except (IndexError, KeyError):
                # Occurs when Sigma Mitre Att&ck list is out of date
                continue

            yield {
                "tactic": {
                    "id": tactic_id,
                    "reference": f"https://attack.mitre.org/tactics/{tactic_id}",
                    "name": tactic.title().replace("_", " "),
                },
                "framework": "MITRE ATT&CK",
                "technique": [
                    {
                        "id": technique,
                        "reference": f"https://attack.mitre.org/techniques/{technique}",
                        "name": technique_name,
                        "subtechnique": sub_techniques,
                    }
                ],
            }

        for tag in attack_tags:
            tags.remove(tag)

    def finalize_query_dsl_lucene(
        self, rule: SigmaRule, query: str, index: int, state: ConversionState
    ) -> Dict:
        return {
            "query": {
                "bool": {
                    "must": [
                        {"query_string": {"query": query, "analyze_wildcard": True}}
                    ]
                }
            }
        }

    def finalize_output_dsl_lucene(self, queries: List[Dict]) -> Dict:
        return list(queries)

    def finalize_query_kibana_ndjson(
        self, rule: SigmaRule, query: str, index: int, state: ConversionState
    ) -> Dict:
        # TODO: implement the per-query output for the output format kibana here. Usually, the
        # generated query is embedded into a template, e.g. a JSON format with additional
        # information from the Sigma rule.
        columns = []
        index = "beats-*"
        ndjson = {
            "id": str(rule.id),
            "type": "search",
            "attributes": {
                "title": f"SIGMA - {rule.title}",
                "description": rule.description,
                "hits": 0,
                "columns": columns,
                "sort": ["@timestamp", "desc"],
                "version": 1,
                "kibanaSavedObjectMeta": {
                    "searchSourceJSON": str(
                        json.dumps(
                            {
                                "index": index,
                                "filter": [],
                                "highlight": {
                                    "pre_tags": ["@kibana-highlighted-field@"],
                                    "post_tags": ["@/kibana-highlighted-field@"],
                                    "fields": {"*": {}},
                                    "require_field_match": False,
                                    "fragment_size": 2147483647,
                                },
                                "query": {
                                    "query_string": {
                                        "query": query,
                                        "analyze_wildcard": True,
                                    }
                                },
                            }
                        )
                    )
                },
            },
            "references": [
                {
                    "id": index,
                    "name": "kibanaSavedObjectMeta.searchSourceJSON.index",
                    "type": "index-pattern",
                }
            ],
        }
        return ndjson

    def finalize_output_kibana_ndjson(self, queries: List[str]) -> List[Dict]:
        # TODO: implement the output finalization for all generated queries for the format kibana
        # here. Usually, the single generated queries are embedded into a structure, e.g. some
        # JSON or XML that can be imported into the SIEM.
        return list(queries)

    def finalize_query_siem_rule(
        self, rule: SigmaRule, query: str, index: int, state: ConversionState
    ) -> Dict:
        """
        Create SIEM Rules in JSON Format. These rules could be imported into Kibana using the
        Create Rule API https://www.elastic.co/guide/en/kibana/8.6/create-rule-api.html
        This API (and generated data) is NOT the same like importing Detection Rules via:
        Kibana -> Security -> Alerts -> Manage Rules -> Import
        If you want to have a nice importable NDJSON File for the Security Rule importer
        use pySigma Format 'siem_rule_ndjson' instead.
        """

        siem_rule = {
            "name": f"SIGMA - {rule.title}",
            "consumer": "siem",
            "enabled": True,
            "throttle": None,
            "schedule": {
                "interval": f"{self.schedule_interval}{self.schedule_interval_unit}"
            },
            "params": {
                "author": [rule.author] if rule.author is not None else [],
                "description": (
                    rule.description
                    if rule.description is not None
                    else "No description"
                ),
                "ruleId": str(rule.id),
                "falsePositives": rule.falsepositives,
                "from": f"now-{self.schedule_interval}{self.schedule_interval_unit}",
                "immutable": False,
                "license": "DRL",
                "outputIndex": "",
                "meta": {
                    "from": "1m",
                },
                "maxSignals": 100,
                "riskScore": (
                    self.severity_risk_mapping[rule.level.name]
                    if rule.level is not None
                    else 21
                ),
                "riskScoreMapping": [],
                "severity": (
                    str(rule.level.name).lower() if rule.level is not None else "low"
                ),
                "severityMapping": [],
                "threat": list(self.finalize_output_threat_model(rule.tags)),
                "to": "now",
                "references": rule.references,
                "version": 1,
                "exceptionsList": [],
                "relatedIntegrations": [],
                "requiredFields": [],
                "setup": "",
                "type": "query",
                "language": "lucene",
                "index": self.index_names,
                "query": query,
                "filters": [],
            },
            "rule_type_id": "siem.queryRule",
            "tags": [f"{n.namespace}-{n.name}" for n in rule.tags],
            "notify_when": "onActiveAlert",
            "actions": [],
        }
        return siem_rule

    def finalize_output_siem_rule(self, queries: List[Dict]) -> Dict:
        return list(queries)

    def finalize_query_siem_rule_ndjson(
        self, rule: SigmaRule, query: str, index: int, state: ConversionState
    ) -> Dict:
        """
        Generating SIEM/Detection Rules in NDJSON Format. Compatible with

        https://www.elastic.co/guide/en/security/8.6/rules-ui-management.html#import-export-rules-ui
        """

        siem_rule = {
            "id": str(rule.id),
            "name": f"SIGMA - {rule.title}",
            "enabled": True,
            "throttle": "no_actions",
            "interval": f"{self.schedule_interval}{self.schedule_interval_unit}",
            "author": [rule.author] if rule.author is not None else [],
            "description": (
                rule.description if rule.description is not None else "No description"
            ),
            "rule_id": str(rule.id),
            "false_positives": rule.falsepositives,
            "from": f"now-{self.schedule_interval}{self.schedule_interval_unit}",
            "immutable": False,
            "license": "DRL",
            "output_index": "",
            "meta": {
                "from": "1m",
            },
            "max_signals": 100,
            "risk_score": (
                self.severity_risk_mapping[rule.level.name]
                if rule.level is not None
                else 21
            ),
            "risk_score_mapping": [],
            "severity": (
                str(rule.level.name).lower() if rule.level is not None else "low"
            ),
            "severity_mapping": [],
            "threat": list(self.finalize_output_threat_model(rule.tags)),
            "tags": [f"{n.namespace}-{n.name}" for n in rule.tags],
            "to": "now",
            "references": rule.references,
            "version": 1,
            "exceptions_list": [],
            "related_integrations": [],
            "required_fields": [],
            "setup": "",
            "type": "query",
            "language": "lucene",
            "index": self.index_names,
            "query": query,
            "filters": [],
            "actions": [],
        }
        return siem_rule

    def finalize_output_siem_rule_ndjson(self, queries: List[Dict]) -> Dict:
        return list(queries)
