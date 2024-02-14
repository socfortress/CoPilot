from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class ProvisionSapSiemRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    time_interval: int = Field(
        ...,
        description="The time interval for the scheduler.",
        examples=[5],
    )
    integration_name: str = Field(
        "SAP SIEM",
        description="The integration name.",
        examples=["SAP SIEM"],
    )

    # ensure the `integration_name` is always set to "Mimecast"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "SAP SIEM"
        return values


class ProvisionSapSiemResponse(BaseModel):
    success: bool
    message: str


# ! STREAMS ! #
class StreamRule(BaseModel):
    field: str
    type: int
    inverted: bool
    value: str


class SapSiemEventStream(BaseModel):
    title: str = Field(..., description="Title of the stream")
    description: str = Field(..., description="Description of the stream")
    index_set_id: str = Field(..., description="ID of the associated index set")
    rules: List[StreamRule] = Field(..., description="List of rules for the stream")
    matching_type: str = Field(..., description="Matching type for the rules")
    remove_matches_from_default_stream: bool = Field(
        ...,
        description="Whether to remove matches from the default stream",
    )
    content_pack: Optional[str] = Field(
        None,
        description="Associated content pack, if any",
    )

    class Config:
        schema_extra = {
            "example": {
                "title": "SAP SIEM EVENTS - Example Company",
                "description": "SAP SIEM EVENTS - Example Company",
                "index_set_id": "12345",
                "rules": [
                    {
                        "field": "customer_code",
                        "type": 1,
                        "inverted": False,
                        "value": "ExampleCode",
                    },
                    {
                        "field": "integration",
                        "type": 1,
                        "inverted": False,
                        "value": "sap_siem",
                    },
                ],
                "matching_type": "AND",
                "remove_matches_from_default_stream": True,
                "content_pack": None,
            },
        }
