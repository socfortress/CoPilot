from typing import List
from typing import Optional

from pydantic import BaseModel


class Stage(BaseModel):
    match: str
    rules: List[str]
    stage: int


class StageWithRuleID(Stage):
    rule_ids: List[Optional[str]]  # Add a new field to store rule IDs


class Pipeline(BaseModel):
    created_at: str
    description: Optional[str] = None  # Make description optional
    errors: Optional[None]
    id: str
    modified_at: Optional[str] = None  # Make modified_at optional
    source: str
    stages: List[Stage]
    title: str


class GraylogPipelinesResponse(BaseModel):
    message: str
    pipelines: List[Pipeline]
    success: bool


class PipelineRule(BaseModel):
    created_at: str
    description: Optional[str] = None  # Make description optional
    errors: Optional[None]
    id: str
    modified_at: Optional[str] = None # Make modified_at optional
    source: str
    title: str


# Define the main response model
class PipelineRulesResponse(BaseModel):
    message: str
    pipeline_rules: List[PipelineRule]
    success: bool


class PipelineWithRuleID(Pipeline):
    stages: List[StageWithRuleID]  # Override the `stages` field with the new class


class GraylogPipelinesResponseWithRuleID(BaseModel):
    message: str
    pipelines: List[PipelineWithRuleID]
    success: bool


# Creation of Pipelines
class CreatePipelineRule(BaseModel):
    title: str
    description: str
    source: str


class CreatePipeline(BaseModel):
    title: str
    description: str
    source: str


class ModifyPipeline(BaseModel):
    pipeline_id: str
    source: str
