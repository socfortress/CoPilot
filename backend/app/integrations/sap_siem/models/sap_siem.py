from datetime import datetime
from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel


class SapSiemMultipleLogins(SQLModel, table=True):
    """
    Represents the SAP SIEM multiple logins table.
    Table is used to track when an IP has successfully logged in with multiple loginIDs.
    Used in the SAP SIEM integration.
    """

    __tablename__ = "sap_siem_multiple_logins"
    id: Optional[int] = Field(primary_key=True)
    ip: str = Field(description="The IP involved in the case.")
    last_case_created_timestamp: datetime = Field(
        description="Timestamp of the last case created.",
    )
    associated_loginIDs: str = Field(
        description="Comma-separated loginIDs associated with this IP.",
    )
