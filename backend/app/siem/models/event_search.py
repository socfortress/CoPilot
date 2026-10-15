"""What event search remembers for a user, per customer (#1258).

Kept on the server so a user finds their searches and columns on any device. Three
tables, each row owned by one user *and* one customer:

- ``event_search_saved_query``: searches saved under a name, unique per user and customer
  (MySQL's default collation compares it case-insensitively, as the UI does);
- ``event_search_recent_query``: the last searches run, trimmed by the service;
- ``event_search_columns``: the columns a user picked for one event source.

Both keys are hard foreign keys with ``ON DELETE CASCADE``: deleting the user or the
customer takes their rows with it. ``source_name`` is the event source's name, not a
foreign key: a search saved on a source the SOC later removes stays listed, and the
portal says the source is gone instead of losing the user's work.
"""

from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlmodel import Field
from sqlmodel import SQLModel

from app.time_utils import now_utc


def _user_fk() -> Column:
    return Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)


def _customer_fk() -> Column:
    return Column(String(50), ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=False)


class EventSearchState(SQLModel):
    """Everything that makes a search: run it again and the same events come back.

    ``time_mode`` ``relative`` reads ``time_amount`` + ``time_unit`` (``h`` / ``d`` / ``w``);
    ``absolute`` reads ``time_from`` / ``time_to`` (naive UTC).
    """

    source_name: str = Field(max_length=255, nullable=False)
    query: str = Field(default="", sa_type=Text, nullable=False)
    time_mode: str = Field(max_length=16, nullable=False)
    time_amount: int = Field(nullable=False)
    time_unit: str = Field(max_length=1, nullable=False)
    time_from: Optional[datetime] = Field(default=None, nullable=True)
    time_to: Optional[datetime] = Field(default=None, nullable=True)
    page_size: int = Field(nullable=False)


class EventSearchSavedQuery(EventSearchState, table=True):
    __tablename__ = "event_search_saved_query"
    __table_args__ = (UniqueConstraint("user_id", "customer_code", "name", name="uq_event_search_saved_query"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=_user_fk())
    customer_code: str = Field(sa_column=_customer_fk())
    name: str = Field(max_length=80, nullable=False)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)


class EventSearchRecentQuery(EventSearchState, table=True):
    __tablename__ = "event_search_recent_query"
    __table_args__ = (Index("ix_event_search_recent_query_owner", "user_id", "customer_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=_user_fk())
    customer_code: str = Field(sa_column=_customer_fk())
    ran_at: datetime = Field(default_factory=now_utc, nullable=False)


class EventSearchColumns(SQLModel, table=True):
    __tablename__ = "event_search_columns"
    __table_args__ = (UniqueConstraint("user_id", "customer_code", "source_name", name="uq_event_search_columns"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=_user_fk())
    customer_code: str = Field(sa_column=_customer_fk())
    source_name: str = Field(max_length=255, nullable=False)
    # [{"key": "agent_name", "label": "Host"}, …], in display order
    columns: List[Dict[str, str]] = Field(sa_column=Column(JSON, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)
