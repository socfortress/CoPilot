from enum import Enum
from typing import Any
from typing import List

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field


class AvailableContentPacks(str, Enum):
    SOCFORTRESS_WAZUH_CONTENT_PACK = (
        "The Wazuh Content Pack which includes Input, Stream, Pipeline Rules,"
        " Pipelines, and Lookup Tables for Wazuh logs and the SOCFortress SIEM stack."
    )


class ContentPack(BaseModel):
    name: str
    description: str


class AvailableContentPacksResponse(BaseModel):
    available_content_packs: List[ContentPack] = Field(
        ...,
        example={
            "name": AvailableContentPacks.SOCFORTRESS_WAZUH_CONTENT_PACK.name,
            "description": AvailableContentPacks.SOCFORTRESS_WAZUH_CONTENT_PACK.value,
        },
        description="The available content packs for provisioning in Graylog",
    )
    success: bool = Field(
        ...,
        example=True,
        description="Success of the request to get available content packs",
    )
    message: str = Field(
        ...,
        example="Available content packs retrieved successfully",
        description="Message from the request to get available content packs",
    )


class ProvisionContentPackRequest(BaseModel):
    content_pack_name: AvailableContentPacks = Field(
        ...,
        example=AvailableContentPacks.SOCFORTRESS_WAZUH_CONTENT_PACK,
        description="The name of the content pack to provision in Graylog",
    )

    def __init__(self, **data: Any):
        content_pack_name = data.get("content_pack_name")
        try:
            data["content_pack_name"] = AvailableContentPacks[content_pack_name]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Content pack {content_pack_name} is not available. Please choose from the available content packs.",
            )
        super().__init__(**data)


class ProvisionGraylogResponse(BaseModel):
    success: bool = Field(
        ...,
        example=True,
        description="Success of the Graylog provisioning",
    )
    message: str = Field(
        ...,
        example="Graylog provisioned successfully",
        description="Message from the Graylog provisioning",
    )
