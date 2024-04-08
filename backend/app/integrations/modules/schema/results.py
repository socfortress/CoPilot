from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import Extra


class CopilotResponse(BaseModel):
    message: str
    success: bool
    module_name: str

    class Config:
        extra = Extra.allow
