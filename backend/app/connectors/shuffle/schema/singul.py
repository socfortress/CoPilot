from pydantic import BaseModel
from pydantic import Field


class SingulRequest(BaseModel):
    app: str = Field(..., description="The name of the application", examples=["outlook_office365"])
