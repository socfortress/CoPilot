from typing import List
from pydantic import BaseModel

class Job(BaseModel):
    id: str
    name: str

class JobsResponse(BaseModel):
    jobs: List[Job]
    success: bool
    message: str
