from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field
from sqlmodel import SQLModel


class JobMetadata(SQLModel, table=True):
    __tablename__ = "scheduled_job_metadata"
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True)  # Corresponds to the APScheduler job ID
    last_success: Optional[datetime] = None
    time_interval: int  # The frequency of the job in minutes
    extra_data: Optional[str] = None  # Extra data for the job
    enabled: bool  # Indicates if the job is active or not
    job_description: Optional[str] = Field(max_length=1024)  # Description of the job


class CreateSchedulerRequest(BaseModel):
    function_name: str
    job_id: str
    time_interval: int
