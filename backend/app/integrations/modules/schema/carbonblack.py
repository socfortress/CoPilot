from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


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
    carbonblack_api_url: str = Field(..., example="https://127.0.0.1")
    carbonblack_api_key: str = Field(..., example="1234567890")
    carbonblack_api_id: str = Field(..., example="1234567890")
    carbonblack_org_key: str = Field(..., example="1234567890")
    time_range: Optional[str] = Field(
        "-15m",
        example="-15m",
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
    integration: str = Field(..., example="carbonblack")
    customer_code: str = Field(..., example="socfortress")
    graylog_host: str = Field(..., example="127.0.0.1")
    graylog_port: str = Field(..., example=12201)
    carbonblack_api_url: str = Field(..., example="https://127.0.0.1")
    carbonblack_api_key: str = Field(..., example="1234567890")
    carbonblack_api_id: str = Field(..., example="1234567890")
    carbonblack_org_key: str = Field(..., example="1234567890")
    time_range: Optional[str] = Field(
        "-15m",
        example="-15m",
    )

    @validator("integration")
    def check_integration(cls, v):
        if v != "carbonblack":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'carbonblack' is supported.",
            )
        return v
