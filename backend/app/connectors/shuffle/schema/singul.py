from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class SingulRequest(BaseModel):
    app: str = Field(..., description="The name of the application", example="outlook_office365")
