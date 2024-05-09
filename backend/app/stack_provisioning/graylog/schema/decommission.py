from enum import Enum
from typing import Any

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from pydantic import Field


class AvailableNetworkConnectors(str, Enum):
    FORTINET = (
        "The Fortinet Network Connector which includes Input, Stream, Pipeline Rules,"
        " Pipelines, and Lookup Tables for Fortinet logs and the SOCFortress SIEM stack."
    )
    CROWDSTRIKE = (
        "The Crowdstrike Network Connector which includes Input, Stream, Pipeline Rules,"
        " Pipelines, and Lookup Tables for Crowdstrike logs and the SOCFortress SIEM stack."
    )


class DecommissionNetworkContentPackRequest(BaseModel):
    network_connector: AvailableNetworkConnectors = Field(
        ...,
        example=AvailableNetworkConnectors.FORTINET.name,
        description="The name of the content pack to provision in Graylog",
    )
    customer_code: str = Field(
        ...,
        description="The customer code for the content pack to provision in Graylog",
        example="00001",
    )

    def __init__(self, **data: Any):
        network_connector = data.get("network_connector")
        if network_connector:
            network_connector = network_connector.upper()
            logger.info(f"Network Connector: {network_connector}")
        try:
            data["network_connector"] = AvailableNetworkConnectors[network_connector]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"{network_connector} is not available. Please choose from the available network connectors.",
            )
        super().__init__(**data)


class DecommissionNetworkContentPackResponse(BaseModel):
    message: str = Field(
        ...,
        example="FORTINET Content Pack decommissioned successfully",
        description="Message from the request to decommission a content pack",
    )
    success: bool = Field(
        ...,
        example=True,
        description="Success of the request to decommission a content pack",
    )
