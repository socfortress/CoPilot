from pydantic import BaseModel, Field

######### ! SEND TO SHUFFLE PAYLOAD ! #########
class ShufflePayload(BaseModel):
    alert_id: str = Field(
        ...,
        description="The alert ID.",
        examples="123456789",
    )
    customer: str = Field(
        ...,
        description="The customer name.",
        examples="SOCFortress",
    )
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples="socfortress",
    )
    alert_source_link: str = Field(
        ...,
        description="The alert source link.",
        examples="https://app.socfortress.co/alerts/123456789",
    )
    rule_description: str = Field(
        ...,
        description="The rule description.",
        examples="Test rule",
    )
    hostname: str = Field(
        ...,
        description="The hostname of the affected asset.",
        examples="test-hostname",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)
