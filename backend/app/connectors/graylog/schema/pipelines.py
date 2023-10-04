from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class Stage(BaseModel):
    match: str
    rules: List[str]
    stage: int


class Pipeline(BaseModel):
    created_at: str
    description: str
    errors: Optional[None]
    id: str
    modified_at: str
    source: str
    stages: List[Stage]
    title: str


class GraylogPipelinesResponse(BaseModel):
    message: str
    pipelines: List[Pipeline]
    success: bool


class PipelineRule(BaseModel):
    created_at: str
    description: str
    errors: Optional[None]
    id: str
    modified_at: str
    source: str
    title: str


# Define the main response model
class PipelineRulesResponse(BaseModel):
    message: str
    pipeline_rules: List[PipelineRule]
    success: bool
