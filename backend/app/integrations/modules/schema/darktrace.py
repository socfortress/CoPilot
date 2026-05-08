from fastapi import HTTPException
from pydantic import field_validator, BaseModel
from pydantic import Field


class InvokeDarktraceRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Darktrace",
        description="The integration name.",
        examples=["Darktrace"],
    )


class DarktraceAuthKeys(BaseModel):
    PUBLIC_TOKEN: str = Field(
        ...,
        description="The API key.",
        examples=["123456"],
    )
    PRIVATE_TOKEN: str = Field(
        ...,
        description="The integration key.",
        examples=["123456"],
    )
    HOST: str = Field(
        ...,
        description="The secret key.",
        examples=["123456"],
    )
    PORT: str = Field(
        ...,
        description="The secret key.",
        examples=["123456"],
    )


class InvokeDarktraceResponse(BaseModel):
    success: bool = Field(
        ...,
        description="The success status.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="The message.",
        examples=["Darktrace Events collected successfully."],
    )


class CollectDarktrace(BaseModel):
    integration: str = Field(..., examples=["darktrace"])
    customer_code: str = Field(..., examples=["socfortress"])
    graylog_host: str = Field(..., examples=["127.0.0.1"])
    graylog_port: str = Field(..., examples=[12201])
    public_token: str = Field(..., examples=["public_token"])
    private_token: str = Field(..., examples=["private_token"])
    darktrace_host: str = Field(..., examples=["https://darktrace.local"])
    darktrace_port: str = Field(..., examples=[2026])
    timeframe: str = Field(..., examples=["15m"])

    @field_validator("integration")
    @classmethod
    def check_integration(cls, v):
        if v != "darktrace":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'darktrace' is supported.",
            )
        return v

    @field_validator("timeframe")
    @classmethod
    def validate_range(cls, v):
        if not v.endswith(("m", "h", "d")):
            raise HTTPException(
                status_code=400,
                detail="Invalid range. Use 'm' for minutes, 'h' for hours, or 'd' for days.",
            )
        return v
