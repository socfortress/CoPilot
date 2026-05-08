from fastapi import HTTPException
from pydantic import field_validator, BaseModel
from pydantic import Field


class InvokeDuoRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Duo",
        description="The integration name.",
        examples=["Duo"],
    )


class DuoAuthKeys(BaseModel):
    API_HOSTNAME: str = Field(
        ...,
        description="The API key.",
        examples=["123456"],
    )
    INTEGRATION_KEY: str = Field(
        ...,
        description="The integration key.",
        examples=["123456"],
    )
    SECRET_KEY: str = Field(
        ...,
        description="The secret key.",
        examples=["123456"],
    )


class InvokeDuoResponse(BaseModel):
    success: bool = Field(
        ...,
        description="The success status.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="The message.",
        examples=["Duo Events collected successfully."],
    )


class CollectDuo(BaseModel):
    integration: str = Field(..., examples=["duo"])
    customer_code: str = Field(..., examples=["socfortress"])
    integration_key: str = Field(..., examples=["1234567890"])
    secret_key: str = Field(..., examples=["1234567890"])
    api_host: str = Field(..., examples=["api-1234567890.duosecurity.com"])
    api_endpoint: str = Field(..., examples=["/admin/v2/logs/authentication"])
    graylog_host: str = Field(..., examples=["127.0.0.1"])
    graylog_port: str = Field(..., examples=[12201])
    range: str = Field(..., examples=["15m"])  # New field for range

    @field_validator("integration")
    @classmethod
    def check_integration(cls, v):
        if v != "duo":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'duo' is supported.",
            )
        return v

    @field_validator("range")
    @classmethod
    def validate_range(cls, v):
        if not v.endswith(("m", "h", "d")):
            raise HTTPException(
                status_code=400,
                detail="Invalid range. Use 'm' for minutes, 'h' for hours, or 'd' for days.",
            )
        return v
