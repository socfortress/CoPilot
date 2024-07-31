from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from uuid import uuid4

from sqlalchemy import ForeignKey
from sqlalchemy import PrimaryKeyConstraint
from sqlmodel import JSON
from sqlmodel import Column
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel
from sqlmodel import Text


class SigmaQuery(SQLModel, table=True):
    __tablename__ = "sigma_queries"
    id: Optional[int] = Field(default=None, primary_key=True)
    rule_name: str = Field(sa_column=Text, nullable=False)
    rule_query: str = Field(sa_column=Text, nullable=False)
    active: bool = Field(default=False)
    time_interval: str = Field(default="1m", nullable=False)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    last_execution_time: Optional[datetime] = Field(default_factory=datetime.utcnow)
