"""The "Talon v2" setting (talon-analyst SPEC §5.3, D54; plan M5-5a, decision a).

One row per Talon connector, keyed by the connector's name, so a second connector (the pilot's
"Talon Next", D53) gets a row of its own. A missing row reads as off: every v2 route answers 404
and CoPilot's Talon UI and proxy stay exactly as they are without it.

A typed table rather than ``connectors.connector_extra_data`` (free text) or a new ``connectors``
column (that table is cached in-process, ``app/connectors/cache.py``). Read and written only
through ``app/connectors/talon/services/talon_v2.py``.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel

from app.time_utils import now_utc


class TalonConnectorSettings(SQLModel, table=True):
    __tablename__ = "talon_connector_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    # ``connectors.connector_name`` (not an FK: that column isn't unique).
    connector_name: str = Field(max_length=256, unique=True, index=True, nullable=False)
    # Off by default: the v2 chat proxy exists only once an admin turns it on.
    v2_enabled: bool = Field(default=False, nullable=False)
    updated_by_user_id: Optional[int] = Field(default=None, nullable=True)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)
