from typing import List

from pydantic import BaseModel
from pydantic import Field


class DecommissionedData(BaseModel):
    agents_deleted: List[str] = Field(
        ...,
        example=["agent1", "agent2"],
        description="List of agents deleted",
    )
    groups_deleted: List[str] = Field(
        ...,
        example=["group1", "group2"],
        description="List of groups deleted",
    )
    stream_deleted: str = Field(..., example="stream1", description="Stream deleted")
    index_deleted: str = Field(..., example="index1", description="Index deleted")


class DecommissionCustomerResponse(BaseModel):
    message: str = Field(
        ...,
        example="Customer decommissioned successfully",
        description="Message indicating the customer was decommissioned successfully",
    )
    success: bool = Field(
        ...,
        example=True,
        description="Whether the customer was decommissioned successfully or not",
    )
    decomissioned_data: DecommissionedData = Field(
        ...,
        description="Data from the decomissioning process",
    )
