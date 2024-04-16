from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class InvokeMimecastRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Mimecast",
        description="The integration name.",
        examples=["Mimecast"],
    )


class MimecastAuthKeys(BaseModel):
    APP_ID: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION ID",
        examples=["00002"],
    )
    APP_KEY: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION KEY",
        examples=["00002"],
    )
    EMAIL_ADDRESS: Optional[str] = Field(
        None,
        description="EMAIL ADDRESS OF YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    ACCESS_KEY: str = Field(
        ...,
        description="ACCESS KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    SECRET_KEY: str = Field(
        ...,
        description="SECRET KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    URI = str = Field(
        "/api/audit/get-siem-logs",
        description="URI FOR YOUR API Endpoint",
        examples=["/api/audit/get-siem-logs"],
    )


class InvokeMimecastResponse(BaseModel):
    success: bool = Field(
        ...,
        description="The success status.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="The message.",
        examples=["Mimecast Events collected successfully."],
    )


class CollectMimecast(BaseModel):
    integration: str = Field(..., example="mimecast")
    customer_code: str = Field(..., example="socfortress")
    graylog_host: str = Field(..., example="127.0.0.1")
    graylog_port: str = Field(..., example=12201)
    app_id: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION ID",
        examples=["00002"],
    )
    app_key: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION KEY",
        examples=["00002"],
    )
    email_address: Optional[str] = Field(
        None,
        description="EMAIL ADDRESS OF YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    access_key: str = Field(
        ...,
        description="ACCESS KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    secret_key: str = Field(
        ...,
        description="SECRET KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    uri: str = Field(
        "/api/audit/get-siem-logs",
        description="URI FOR YOUR API Endpoint",
        examples=["/api/audit/get-siem-logs"],
    )
    time_range: Optional[str] = Field(
        "15m",
        pattern="^[1-9][0-9]*[mhdw]$",
        description="Time range for the query (1m, 1h, 1d, 1w)",
    )

    @validator("integration")
    def check_integration(cls, v):
        if v != "mimecast":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'mimecast' is supported.",
            )
        return v
