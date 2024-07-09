from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class ProvisionDarktraceRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    time_interval: int = Field(
        15,
        description="The time interval for the scheduler.",
        examples=[15],
    )
    integration_name: str = Field(
        "Darktrace",
        description="The integration name.",
        examples=["Darktrace"],
    )

    # ensure the `integration_name` is always set to "Mimecast"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "Darktrace"
        return values


class ProvisionDarktraceResponse(BaseModel):
    success: bool
    message: str


# ! STREAMS ! #
class StreamRule(BaseModel):
    field: str
    type: int
    inverted: bool
    value: str


class DarktraceEventStream(BaseModel):
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
                "title": "Darktrace SIEM EVENTS - Example Company",
                "description": "Darktrace SIEM EVENTS - Example Company",
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
                        "value": "darktrace",
                    },
                ],
                "matching_type": "AND",
                "remove_matches_from_default_stream": True,
                "content_pack": None,
            },
        }
