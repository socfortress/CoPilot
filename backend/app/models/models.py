from datetime import datetime

from loguru import logger
from sqlalchemy.dialects.postgresql import JSONB  # Add this line

from app import db
from app import ma


class ConnectorsAvailable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    connector_name = db.Column(db.String(100), unique=True)
    connector_description = db.Column(db.String(100))
    connector_supports = db.Column(db.String(100))
    connector_configured = db.Column(db.Boolean, default=False)
    connector_verified = db.Column(db.Boolean, default=False)

    def __init__(self, connector_name, connector_supports):
        self.connector_name = connector_name
        self.connector_supports = connector_supports

    def __repr__(self):
        return f"<ConnectorsAvailble {self.connector_name}>"


class ConnectorsAvailableSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "connector_name",
            "connector_description",
            "connector_supports",
            "connector_configured",
            "connector_verified",
        )


connector_available_schema = ConnectorsAvailableSchema()
connectors_available_schema = ConnectorsAvailableSchema(many=True)


# Class for the connector which will store the endpoint url, connector name, connector type, connector last updated,
# username and password
class Connectors(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    connector_name = db.Column(db.String(100), unique=True)
    connector_type = db.Column(db.String(100))
    connector_url = db.Column(db.String(100))
    connector_last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    connector_username = db.Column(db.String(100))
    connector_password = db.Column(db.String(100))
    connector_api_key = db.Column(db.String(100))

    def __init__(
        self,
        connector_name,
        connector_type,
        connector_url,
        connector_username,
        connector_password,
        connector_api_key,
    ):
        self.connector_name = connector_name
        self.connector_type = connector_type
        self.connector_url = connector_url
        self.connector_username = connector_username
        self.connector_password = connector_password
        # If the `connector_name` is `shuffle` or `dfir-irs` then set the `connector_api_key`. Otherwise set it to
        # `None`
        if (
            connector_name.lower() == "shuffle"
            or connector_name.lower() == "dfir-irs"
            or connector_name.lower() == "velociraptor"
        ):
            logger.info(f"Setting the API key for {connector_name}")
            self.connector_api_key = connector_api_key
        else:
            logger.info(f"Not setting the API key for {connector_name}")
            self.connector_api_key = None

    def __repr__(self):
        return f"<Connectors {self.connector_name}>"


class ConnectorsSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "connector_name",
            "connector_type",
            "connector_url",
            "connector_last_updated",
            "connector_username",
            "connector_password",
            "connector_api_key",
        )


connector_schema = ConnectorsSchema()
connectors_schema = ConnectorsSchema(many=True)


# Class for the disabled rule IDs which will store the rule ID, previous configuration, new configuration, reason for
# disabling, date disabled, and the length of time the rule will be disabled for
# Path: backend\app\models.py
# class DisabledRules(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     rule_id = db.Column(db.String(100))
#     previous_level = db.Column(db.String(1000))
#     new_level = db.Column(db.String(1000))
#     reason_for_disabling = db.Column(db.String(100))
#     date_disabled = db.Column(db.DateTime, default=datetime.utcnow)
#     length_of_time = db.Column(db.Integer)

#     def __init__(
#         self,
#         rule_id,
#         previous_level,
#         new_level,
#         reason_for_disabling,
#         length_of_time,
#     ):
#         self.rule_id = rule_id
#         self.previous_level = previous_level
#         self.new_level = new_level
#         self.reason_for_disabling = reason_for_disabling
#         self.length_of_time = length_of_time

#     def __repr__(self):
#         return f"<DisabledRules {self.rule_id}>"


# class DisabledRulesSchema(ma.Schema):
#     class Meta:
#         fields = (
#             "id",
#             "rule_id",
#             "previous_level",
#             "new_level",
#             "reason_for_disabling",
#             "date_disabled",
#             "length_of_time",
#         )


# disabled_rule_schema = DisabledRulesSchema()
# disabled_rules_schema = DisabledRulesSchema(many=True)


# Class for Wazuh Indexer allocation which stores disk stats and the host.
# Generate timestamp for each entry and invoke every 5 minutes.
# Path: backend\app\models.py
class WazuhIndexerAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    node = db.Column(db.String(100))
    disk_used = db.Column(db.Float)
    disk_available = db.Column(db.Float)
    disk_total = db.Column(db.Float)
    disk_percent = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        node,
        disk_used,
        disk_available,
        disk_total,
        disk_percent,
    ):
        self.node = node
        self.disk_used = disk_used
        self.disk_available = disk_available
        self.disk_total = disk_total
        self.disk_percent = disk_percent

    def __repr__(self):
        return f"<WazuhIndexerAllocation {self.node}>"


class WazuhIndexerAllocationSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "node",
            "disk_used",
            "disk_available",
            "disk_total",
            "disk_percent",
            "timestamp",
        )


wazuh_indexer_allocation_schema = WazuhIndexerAllocationSchema()
wazuh_indexer_allocations_schema = WazuhIndexerAllocationSchema(many=True)


# Class for Graylog allocation which stores throughput metrics
# Generate timestamp for each entry and invoke every 5 minutes.
# Path: backend\app\models.py
class GraylogMetricsAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input_usage = db.Column(db.Float)
    output_usage = db.Column(db.Float)
    processor_usage = db.Column(db.Float)
    input_1_sec_rate = db.Column(db.Float)
    output_1_sec_rate = db.Column(db.Float)
    total_input = db.Column(db.Float)
    total_output = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        input_usage,
        output_usage,
        processor_usage,
        input_1_sec_rate,
        output_1_sec_rate,
        total_input,
        total_output,
    ):
        self.input_usage = input_usage
        self.output_usage = output_usage
        self.processor_usage = processor_usage
        self.input_1_sec_rate = input_1_sec_rate
        self.output_1_sec_rate = output_1_sec_rate
        self.total_input = total_input
        self.total_output = total_output

    def __repr__(self):
        return f"<GraylogMetricsAllocation {self.id}>"


class GraylogMetricsAllocationSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "input_usage",
            "output_usage",
            "processor_usage",
            "input_1_sec_rate",
            "output_1_sec_rate",
            "total_input",
            "total_output",
            "timestamp",
        )


graylog_metrics_allocation_schema = GraylogMetricsAllocationSchema()
graylog_metrics_allocations_schema = GraylogMetricsAllocationSchema(many=True)


# Class for cases which stores the case ID, case name, list of agents
# Path: backend\app\models.py
class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer)
    case_name = db.Column(db.String(100))
    agents = db.Column(db.String(1000))

    def __init__(self, case_id, case_name, agents):
        self.case_id = case_id
        self.case_name = case_name
        self.agents = agents

    def __repr__(self):
        return f"<Case {self.case_id}>"


class CaseSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "case_id",
            "case_name",
            "agents",
        )


case_schema = CaseSchema()
cases_schema = CaseSchema(many=True)


# Class for artifacts collected which stores the artifact name, artificat results (json), hostname
# Path: backend\app\models.py
class Artifact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artifact_name = db.Column(db.String(100))
    artifact_results = db.Column(JSONB)
    hostname = db.Column(db.String(100))

    def __init__(self, artifact_name, artifact_results, hostname):
        self.artifact_name = artifact_name
        self.artifact_results = artifact_results
        self.hostname = hostname

    def __repr__(self):
        return f"<Artifact {self.artifact_name}>"


class ArtifactSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "artifact_name",
            "artifact_results",
            "hostname",
        )


artifact_schema = ArtifactSchema()
artifacts_schema = ArtifactSchema(many=True)
