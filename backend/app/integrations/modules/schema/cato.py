from fastapi import HTTPException
from pydantic import field_validator, BaseModel
from pydantic import Field


class InvokeCatoRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    # ! CASE SENSITIVE ! #
    integration_name: str = Field(
        "CATO",
        description="The integration name.",
        examples=["CATO"],
    )


class CatoAuthKeys(BaseModel):
    API_KEY: str = Field(
        ...,
        description="The API key.",
        examples=["123456"],
    )
    ACCOUNT_ID: int = Field(
        ...,
        description="The account ID.",
        examples=[123456],
    )
    EVENT_TYPES: str = Field(
        ...,
        description="The event types.",
        examples=["Security"],
    )
    EVENT_SUB_TYPES: str = Field(
        ...,
        description="The event sub types.",
        examples=["NG Anti Malware,Anti Malware,IPS"],
    )


class InvokeCatoResponse(BaseModel):
    success: bool = Field(
        ...,
        description="The success status.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="The message.",
        examples=["cato Events collected successfully."],
    )


class CollectCato(BaseModel):
    integration: str = Field(..., examples=["cato"])
    customer_code: str = Field(..., examples=["socfortress"])
    graylog_host: str = Field(..., examples=["127.0.0.1"])
    graylog_port: str = Field(..., examples=[12201])
    api_key: str = Field(..., examples=["1234567890"])
    account_id: int = Field(..., examples=[123456])
    event_types: str = Field(..., examples=["Security"])
    event_sub_types: str = Field(..., examples=["NG Anti Malware,Anti Malware,IPS"])

    @field_validator("integration")
    @classmethod
    def check_integration(cls, v):
        if v != "cato":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'cato' is supported.",
            )
        return v
