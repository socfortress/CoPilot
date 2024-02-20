from pydantic import BaseModel
from pydantic import Field
from enum import Enum
from typing import List

class AvailableContentPacks(str, Enum):
    SOCFORTRESS_WAZUH_CONTENT_PACK = "The Wazuh Content Pack which includes Input, Stream, Pipeline Rules, Piplines, and Lookup Tables for Wazuh logs and the SOCFortress SIEM stack."

class ContentPack(BaseModel):
    name: str
    description: str

class AvailableContentPacksResponse(BaseModel):
    available_content_packs: List[ContentPack] = Field(
        ...,
        example={"name": AvailableContentPacks.SOCFORTRESS_WAZUH_CONTENT_PACK.name, "description": AvailableContentPacks.SOCFORTRESS_WAZUH_CONTENT_PACK.value},
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
