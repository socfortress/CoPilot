from datetime import datetime
from typing import List

from pydantic import BaseModel


class Job(BaseModel):
    id: str
    name: str
    enabled: bool
    time_interval: int


class JobsResponse(BaseModel):
    jobs: List[Job]
    success: bool
    message: str


class JobsNextRunResponse(BaseModel):
    next_run_time: datetime
    success: bool
    message: str
