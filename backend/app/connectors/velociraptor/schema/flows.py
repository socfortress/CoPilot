from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class FlowSpecParameter(BaseModel):
    key: str
    value: str
    comment: Optional[str]


class FlowSpec(BaseModel):
    artifact: str
    parameters: Optional[List[FlowSpecParameter]] = Field(
        None,
        description="The parameters of the artifact.",
    )


class FlowRequest(BaseModel):
    creator: str
    user_data: str
    client_id: str
    flow_id: str
    urgent: bool
    artifacts: List[str]
    specs: Optional[List[FlowSpec]] = Field(
        None,
        description="The specs of the artifacts.",
    )
    cpu_limit: int
    iops_limit: int
    progress_timeout: int
    timeout: int
    max_rows: int
    max_upload_bytes: int
    trace_freq_sec: int
    allow_custom_overrides: bool
    log_batch_time: int
    compiled_collector_args: List[str]
    ops_per_second: int

    @root_validator(pre=True)
    def validate_specs(cls, values):
        if "specs" in values and values["specs"] is not None:
            validated_specs = []
            for spec in values["specs"]:
                try:
                    validated_spec = FlowSpec(**spec)
                    validated_specs.append(validated_spec)
                except Exception as e:
                    # raise HTTPException(status_code=400, detail=f"Failed to validate spec: {e}")
                    logger.error(f"Failed to validate spec: {e}")
            values["specs"] = validated_specs
        return values


class FlowQueryStat(BaseModel):
    status: str
    error_message: str
    backtrace: str
    duration: int
    last_active: int
    first_active: int
    names_with_response: List[str]
    Artifact: str
    log_rows: int
    uploaded_files: int
    uploaded_bytes: int
    expected_uploaded_bytes: int
    result_rows: int
    query_id: int
    total_queries: int


class FlowClientSession(BaseModel):
    client_id: str
    session_id: str
    request: FlowRequest
    backtrace: str
    create_time: int
    start_time: int
    active_time: int
    total_uploaded_files: int
    total_expected_uploaded_bytes: int
    total_uploaded_bytes: int
    total_collected_rows: int
    total_logs: int
    total_requests: int
    outstanding_requests: int
    next_response_id: int
    execution_duration: int
    state: str
    status: str
    artifacts_with_results: List[str]
    query_stats: List[FlowQueryStat]
    uploaded_files: List[str]
    user_notified: bool
    logs: List[str]
    dirty: bool
    total_loads: int


class FlowResponse(BaseModel):
    results: List[FlowClientSession]
    success: bool
    message: str


class RetrieveFlowRequest(BaseModel):
    client_id: str
    session_id: str

    @root_validator(pre=True)
    def validate_session_id(cls, values):
        if "session_id" in values and values["session_id"] == "":
            raise HTTPException(
                status_code=400,
                detail="The session_id cannot be an empty string",
            )
        return values
