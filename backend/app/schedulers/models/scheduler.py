from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class JobMetadata(SQLModel, table=True):
    __tablename__ = "scheduled_job_metadata"
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True)  # Corresponds to the APScheduler job ID
    last_success: Optional[datetime] = None
    time_interval: int  # The frequency of the job in minutes
    enabled: bool  # Indicates if the job is active or not
