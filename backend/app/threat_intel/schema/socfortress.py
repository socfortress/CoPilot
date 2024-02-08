from typing import Optional

from pydantic import BaseModel, Field


class SocfortressThreatIntelRequest(BaseModel):
    ioc_value: str
    customer_code: Optional[str] = Field(
        "socfortress_copilot", description="The customer code for the customer",
    )


class IoCMapping(BaseModel):
    comment: Optional[str] = Field(None, description="Comment about the IOCs")
    ioc_source: str = Field(
        "SOCFortress Threat Intel", description="Identifier for the source of the IOC",
    )
    report_url: Optional[str] = Field(None, description="URL for the related report")
    score: Optional[int] = Field(
        None,
        description="Score indicating the severity or importance",
    )
    timestamp: Optional[str] = Field(None, description="Timestamp for the data")
    type: Optional[str] = Field(
        None,
        description="Type of indicator, e.g., Domain-Name",
    )
    value: Optional[str] = Field(None, description="The actual value of the indicator")
    virustotal_url: Optional[str] = Field(
        None,
        description="URL to the VirusTotal report",
    )

    def to_dict(self):
        return self.dict()


class IoCResponse(BaseModel):
    data: Optional[IoCMapping] = Field(None, description="The data for the IoC")
    success: bool = Field(..., description="Indicates if it was successful")
    message: Optional[str] = Field(None, description="Message about the IoC")

    def to_dict(self):
        return self.dict()
