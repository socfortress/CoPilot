from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

# pyvelociraptor is pure gRPC transport: the shape of a `flows()` row is whatever
# the Velociraptor server version emits and can change between minor versions
# (see CLAUDE.md). These schemas are therefore deliberately tolerant — every field
# is optional with a type-matching default and unknown keys are ignored — so a
# single missing/renamed field on one flow can't 500 the whole endpoint.


class FlowSpecParameter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str = ""
    value: str = ""
    comment: Optional[str] = None


class FlowSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    artifact: str = ""
    parameters: Optional[List[FlowSpecParameter]] = Field(
        None,
        description="The parameters of the artifact.",
    )


class FlowRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    creator: str = ""
    user_data: str = ""
    client_id: str = ""
    flow_id: str = ""
    urgent: bool = False
    artifacts: List[str] = Field(default_factory=list)
    specs: Optional[List[FlowSpec]] = Field(
        None,
        description="The specs of the artifacts.",
    )
    cpu_limit: int = 0
    iops_limit: int = 0
    progress_timeout: int = 0
    timeout: int = 0
    max_rows: int = 0
    max_upload_bytes: int = 0
    trace_freq_sec: int = 0
    allow_custom_overrides: bool = False
    log_batch_time: int = 0
    compiled_collector_args: List[str] = Field(default_factory=list)
    ops_per_second: int = 0

    @model_validator(mode="before")
    @classmethod
    def validate_specs(cls, values):
        if isinstance(values, dict) and values.get("specs") is not None:
            validated_specs = []
            for spec in values["specs"]:
                try:
                    validated_spec = FlowSpec(**spec)
                    validated_specs.append(validated_spec)
                except Exception as e:
                    logger.error(f"Failed to validate spec: {e}")
            values["specs"] = validated_specs
        return values


class FlowQueryStat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = ""
    error_message: str = ""
    backtrace: str = ""
    duration: int = 0
    last_active: int = 0
    first_active: int = 0
    names_with_response: List[str] = Field(default_factory=list)
    Artifact: str = ""
    log_rows: int = 0
    uploaded_files: int = 0
    uploaded_bytes: int = 0
    expected_uploaded_bytes: int = 0
    result_rows: int = 0
    query_id: int = 0
    total_queries: int = 0


class FlowClientSession(BaseModel):
    model_config = ConfigDict(extra="ignore")

    client_id: str = ""
    session_id: str = ""
    request: FlowRequest = Field(default_factory=FlowRequest)
    backtrace: str = ""
    create_time: int = 0
    start_time: int = 0
    active_time: int = 0
    total_uploaded_files: int = 0
    total_expected_uploaded_bytes: int = 0
    total_uploaded_bytes: int = 0
    total_collected_rows: int = 0
    total_logs: int = 0
    total_requests: int = 0
    outstanding_requests: int = 0
    next_response_id: int = 0
    execution_duration: int = 0
    state: str = ""
    status: str = ""
    artifacts_with_results: List[str] = Field(default_factory=list)
    query_stats: List[FlowQueryStat] = Field(default_factory=list)
    uploaded_files: List[str] = Field(default_factory=list)
    user_notified: bool = False
    logs: List[str] = Field(default_factory=list)
    dirty: bool = False
    total_loads: int = 0


class FlowResponse(BaseModel):
    results: List[FlowClientSession]
    success: bool
    message: str


class RetrieveFlowRequest(BaseModel):
    client_id: str
    session_id: str

    @model_validator(mode="before")
    @classmethod
    def validate_session_id(cls, values):
        if "session_id" in values and values["session_id"] == "":
            raise HTTPException(
                status_code=400,
                detail="The session_id cannot be an empty string",
            )
        return values
