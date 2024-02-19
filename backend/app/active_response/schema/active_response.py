from enum import Enum
from pydantic import BaseModel
from typing import List

class ActiveResponsesSupported(Enum):
    WINDOWS_FIREWALL = "Block or unblock any outbound traffic to the defined IP address via the Windows Firewall"
    # Add more active responses here as needed


class ActiveResponse(BaseModel):
    name: str
    description: str

class ActiveResponsesSupportedResponse(BaseModel):
    supported_active_responses: List[ActiveResponse]
    success: bool
    message: str

class ActiveResponseDetails(BaseModel):
    name: str
    description: str
    markdown_content: str

    class Config:
        json_encoders = {
            str: lambda v: v.encode('utf-8', 'ignore').decode('utf-8')
        }
