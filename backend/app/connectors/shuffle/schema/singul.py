from pydantic import BaseModel
from pydantic import Field


class SingulRequest(BaseModel):
    app: str = Field(..., description="The name of the application", example="outlook_office365")
