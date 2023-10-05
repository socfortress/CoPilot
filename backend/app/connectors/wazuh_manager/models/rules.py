import datetime
from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel


class DisabledRule(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    rule_id: str = Field(index=True)
    previous_level: str = Field(max_length=256)
    new_level: str = Field(max_length=256)
    reason_for_disabling: str = Field(max_length=256)
    length_of_time: str = Field(max_length=256)
    date_disabled: datetime.datetime = datetime.datetime.now()
    disabled_by: str = Field(max_length=256)
