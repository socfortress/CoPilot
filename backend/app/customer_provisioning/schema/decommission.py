from typing import List

from pydantic import BaseModel
from pydantic import Field


class DecommissionedData(BaseModel):
    agents_deleted: List[str] = Field(
        ...,
        examples=[["agent1", "agent2"]],
        description="List of agents deleted",
    )
    groups_deleted: List[str] = Field(
        ...,
        examples=[["group1", "group2"]],
        description="List of groups deleted",
    )
    stream_deleted: str = Field(..., examples=["stream1"], description="Stream deleted")
    index_deleted: str = Field(..., examples=["index1"], description="Index deleted")


class DecommissionCustomerResponse(BaseModel):
    message: str = Field(
        ...,
        examples=["Customer decommissioned successfully"],
        description="Message indicating the customer was decommissioned successfully",
    )
    success: bool = Field(
        ...,
        examples=[True],
        description="Whether the customer was decommissioned successfully or not",
    )
    decomissioned_data: DecommissionedData = Field(
        ...,
        description="Data from the decomissioning process",
    )
