from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class InvokeCarbonBlackRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "CarbonBlack",
        description="The integration name.",
        examples=["CarbonBlack"],
    )


class CarbonBlackAuthKeys(BaseModel):
    carbonblack_api_url: str = Field(..., examples=["https://127.0.0.1"])
    carbonblack_api_key: str = Field(..., examples=["1234567890"])
    carbonblack_api_id: str = Field(..., examples=["1234567890"])
    carbonblack_org_key: str = Field(..., examples=["1234567890"])
    time_range: Optional[str] = Field(
        "-15m",
        examples=["-15m"],
        description="The time range to collect events.",
    )


class InvokeCarbonBlackResponse(BaseModel):
    success: bool = Field(
        ...,
        description="The success status.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="The message.",
        examples=["CarbonBlack Events collected successfully."],
    )


class CollectCarbonBlack(BaseModel):
    integration: str = Field(..., examples=["carbonblack"])
    customer_code: str = Field(..., examples=["socfortress"])
    graylog_host: str = Field(..., examples=["127.0.0.1"])
    graylog_port: str = Field(..., examples=[12201])
    carbonblack_api_url: str = Field(..., examples=["https://127.0.0.1"])
    carbonblack_api_key: str = Field(..., examples=["1234567890"])
    carbonblack_api_id: str = Field(..., examples=["1234567890"])
    carbonblack_org_key: str = Field(..., examples=["1234567890"])
    time_range: Optional[str] = Field(
        "-15m",
        examples=["-15m"],
    )

    @field_validator("integration")
    @classmethod
    def check_integration(cls, v):
        if v != "carbonblack":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'carbonblack' is supported.",
            )
        return v
