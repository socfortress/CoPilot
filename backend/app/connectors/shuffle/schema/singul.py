from pydantic import BaseModel
from pydantic import Field


class SingulRequest(BaseModel):
    app: str = Field(..., description="The name of the application", example="outlook_office365")
    org_id: str = Field(..., description="The organization ID", example="org_12345")
