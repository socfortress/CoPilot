from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class RuleDisable(BaseModel):
    rule_id: str
    reason_for_disabling: str
    length_of_time: str


class RuleDisableResponse(BaseModel):
    previous_level: Optional[str]
    message: str
    success: bool


class RuleEnable(BaseModel):
    rule_id: str
    reason_for_enabling: str


class RuleEnableResponse(BaseModel):
    new_level: Optional[str]
    message: str
    success: bool


class AllDisabledRule(BaseModel):
    rule_id: str
    previous_level: str
    new_level: str
    reason_for_disabling: str
    length_of_time: str
    disabled_by: str


class AllDisabledRuleResponse(BaseModel):
    disabled_rules: List[AllDisabledRule]
    success: bool
    message: str


class RuleExclude(BaseModel):
    rule_value: str = Field(
        ...,
        description="The value of the field trying to be exclude",
        example="C:\\Windows\\ServiceState\\EventLog\\Data\\lastalive1.dat",
    )
    input_value: str = Field(
        ...,
        description="The proposed value of the field trying to be exclude that would result in an exclusiong",
        example="C:\\\\Windows\\\\ServiceState\\\\EventLog\\\\Data\\\\lastalive1\.dat",
    )


class RuleExcludeResponse(BaseModel):
    success: bool
    message: str
    recommended_exclusion: str = Field(
        ...,
        description="The recommended exclusion for the rule",
        example="C:\\\\Windows\\\\ServiceState\\\\EventLog\\\\Data\\\\lastalive1\.dat",
    )
