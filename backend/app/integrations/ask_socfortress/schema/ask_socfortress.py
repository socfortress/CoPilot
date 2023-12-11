from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

class AskSocfortressSigmaRequest(BaseModel):
    sigma_rule_name: str = Field(..., title="Sigma rule name")

class AskSocfortressSigmaResponse(BaseModel):
    message: str = Field(..., title="Message")
    success: bool = Field(..., title="Success")
