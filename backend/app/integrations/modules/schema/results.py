from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class CopilotResponse(BaseModel):
    message: str
    success: bool
    module_name: str
    extra_data: Optional[dict] = Field(
        None,
        description="The Copilot response data.",
    )
