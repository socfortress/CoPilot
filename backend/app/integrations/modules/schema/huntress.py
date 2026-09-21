from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr
from pydantic import field_validator


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
    """The payload posted to the copilot-huntress-module container.

    The credential fields are `SecretStr` so that the model's repr masks them:
    this payload used to be logged in full at INFO on every collection run,
    which put the Wazuh Indexer password and the Huntress API key/secret into
    the backend's docker logs in plaintext. Use `to_wire()` to build the JSON
    body — `model_dump()` deliberately does not yield usable secrets.
    """

    integration: str = Field(..., examples=["huntress"])
    customer_code: str = Field(..., examples=["socfortress"])
    graylog_host: str = Field(..., examples=["127.0.0.1"])
    graylog_port: str = Field(..., examples=[12201])
    wazuh_indexer_host: str = Field(..., examples=["127.0.0.1"])
    wazuh_indexer_username: str = Field(..., examples=["admin"])
    wazuh_indexer_password: SecretStr = Field(..., examples=["admin"])
    api_key: SecretStr = Field(..., examples=["1234567890"])
    api_secret: SecretStr = Field(..., examples=["1234567890"])

    @field_validator("integration")
    @classmethod
    def check_integration(cls, v):
        if v != "huntress":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'huntress' is supported.",
            )
        return v

    def to_wire(self) -> dict:
        """Serialize for the module, with the real secret values restored.

        `model_dump()` returns `SecretStr` objects (not JSON-serializable) and
        `model_dump(mode="json")` returns `"**********"`, so neither can be
        handed to httpx directly. This is the one place the secrets are
        unwrapped, and its result must not be logged.
        """
        payload = self.model_dump()
        for field in ("wazuh_indexer_password", "api_key", "api_secret"):
            payload[field] = getattr(self, field).get_secret_value()
        return payload
