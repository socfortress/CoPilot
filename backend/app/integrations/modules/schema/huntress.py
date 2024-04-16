from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class InvokeHuntressRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Huntress",
        description="The integration name.",
        examples=["Huntress"],
    )


class HuntressAuthKeys(BaseModel):
    API_KEY: str = Field(
        ...,
        description="The API key.",
        examples=["123456"],
    )
    API_SECRET: str = Field(
        ...,
        description="The secret key.",
        examples=["123456"],
    )


class InvokeHuntressResponse(BaseModel):
    success: bool = Field(
        ...,
        description="The success status.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="The message.",
        examples=["Huntress Events collected successfully."],
    )


class CollectHuntress(BaseModel):
    integration: str = Field(..., example="huntress")
    customer_code: str = Field(..., example="socfortress")
    graylog_host: str = Field(..., example="127.0.0.1")
    graylog_port: str = Field(..., example=12201)
    wazuh_indexer_host: str = Field(..., example="127.0.0.1")
    wazuh_indexer_username: str = Field(..., example="admin")
    wazuh_indexer_password: str = Field(..., example="admin")
    api_key: str = Field(..., example="1234567890")
    api_secret: str = Field(..., example="1234567890")

    @validator("integration")
    def check_integration(cls, v):
        if v != "huntress":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'huntress' is supported.",
            )
        return v
