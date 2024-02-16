import re
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


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
