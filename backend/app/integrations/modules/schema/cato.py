from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class InvokeCatoRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "cato",
        description="The integration name.",
        examples=["cato"],
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
    integration: str = Field(..., example="cato")
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
        if v != "cato":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'cato' is supported.",
            )
        return v
