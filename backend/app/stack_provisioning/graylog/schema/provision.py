from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field


class AvailbleContentPacksOverview(str, Enum):
    SOCFORTRESS_WAZUH_CONTENT_PACK = (
        "The Wazuh Content Pack which includes Input, Stream, Pipeline Rules,"
        " Pipelines, and Lookup Tables for Wazuh logs and the SOCFortress SIEM stack."
    )


class AvailableContentPacks(str, Enum):
    SOCFORTRESS_WAZUH_CONTENT_PACK = (
        "The Wazuh Content Pack which includes Input, Stream, Pipeline Rules,"
        " Pipelines, and Lookup Tables for Wazuh logs and the SOCFortress SIEM stack."
    )
    SOCFORTRESS_FORTINET_INPUT_SYSLOG_TCP = "The Fortinet Input Syslog TCP content pack"
    SOCFORTRESS_FORTINET_INPUT_SYSLOG_UDP = "The Fortinet Input Syslog UDP content pack"
    SOCFORTRESS_FORTINET_PROCESSING_PIPELINE = "The Fortinet Processing Pipeline content pack"
    SOCFORTRESS_FORTINET_STREAM = "The Fortinet Stream content pack"
    SOCFORTRESS_CROWDSTRIKE_INPUT_TCP = "The Crowdstrike Input TCP content pack"
    SOCFORTRESS_CROWDSTRIKE_STREAM = "The Crowdstrike Stream content pack"
    SOCFORTRESS_CROWDSTRIKE_PROCESSING_PIPELINE = "The Crowdstrike Processing Pipeline content pack"


class ContentPackKeywords(BaseModel):
    customer_name: Optional[str] = Field(None, description="Name of the customer")
    customer_code: Optional[str] = Field(None, description="Code of the customer")
    protocol_type: Optional[str] = Field(
        None,
        example="TCP",
        description="The protocol type of the content pack",
    )
    syslog_port: Optional[int] = Field(
        None,
        example=514,
        description="The syslog port of the content pack",
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


class ProvisionNetworkContentPackRequest(BaseModel):
    content_pack_name: str = Field(
        ...,
        example="FORTINET",
        description="The name of the content pack to provision in Graylog",
    )
    keywords: Optional[ContentPackKeywords] = Field(
        None,
        description="The keywords of the content pack to provision in Graylog",
    )


class ProvisionContentPackRequest(BaseModel):
    content_pack_name: AvailableContentPacks = Field(
        ...,
        example=AvailableContentPacks.SOCFORTRESS_WAZUH_CONTENT_PACK,
        description="The name of the content pack to provision in Graylog",
    )
    keywords: Optional[ContentPackKeywords] = Field(
        None,
        description="The keywords of the content pack to provision in Graylog",
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


class ReplaceContentPackKeywords(BaseModel):
    REPLACE_UUID_GLOBAL: str = Field(
        ...,
        example="12345678-1234-1234-1234-123456789012",
        description="The UUID of the content pack",
    )
    REPLACE_UUID_SPECIFIC: str = Field(
        ...,
        example="12345678-1234-1234-1234-123456789012",
        description="The UUID of the input",
    )
    customer_name: str = Field(
        ...,
        example="SOCFortress",
        description="The name of the customer",
    )
    customer_code: str = Field(
        ...,
        example="00001",
        description="The code of the customer",
    )
    SYSLOG_PORT: int = Field(
        ...,
        example=514,
        description="The syslog port",
    )
