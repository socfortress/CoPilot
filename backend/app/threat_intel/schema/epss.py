from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class EpssThreatIntelRequest(BaseModel):
    cve: str = Field(
        ...,
        description="The CVE to evaluate.",
    )


class EpssData(BaseModel):
    cve: str
    epss: str
    percentile: str
    date: str


class EpssApiResponse(BaseModel):
    status: str
    status_code: int
    version: str
    access_control_allow_headers: Optional[str]
    access: str
    total: int
    offset: int
    limit: int
    data: List[EpssData]

    def to_dict(self):
        return self.dict()


class EpssThreatIntelResponse(BaseModel):
    data: Optional[List[EpssData]] = Field(None, description="The data for the IoC")
    success: bool = Field(..., description="Indicates if it was successful")
    message: str = Field(None, description="Message about the IoC")
    the_epss_model: str = Field(
        "https://www.first.org/epss/model",
        description="The EPSS model description",
    )
