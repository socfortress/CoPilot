from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

# Branding theme for the generated report: SOCFortress branding (logo + green
# scheme) or the customer portal branding (portal logo + customer brand color).
BrandTheme = Literal["socfortress", "customer"]


class CustomerReportGenerateRequest(BaseModel):
    """Request body for generating a customer incident-management PDF report."""

    customer_code: str
    date_from: datetime
    date_to: datetime
    report_name: Optional[str] = None
    # Whether the generated report is immediately shared with the customer portal.
    # Ignored for customer-generated reports (those are always visible to the customer).
    visible_to_customer: bool = False
    # Which branding to apply to the report. Defaults to the customer portal branding.
    brand_theme: BrandTheme = "customer"

    @model_validator(mode="after")
    def _validate_range(self) -> "CustomerReportGenerateRequest":
        if self.date_from >= self.date_to:
            raise ValueError("date_from must be earlier than date_to")
        return self


class CustomerReportResponse(BaseModel):
    """A single customer incident-management report record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_name: str
    customer_code: str
    file_name: str
    file_size: int
    generated_at: datetime
    generated_by: int
    generated_by_role: Optional[str] = None
    generated_by_name: Optional[str] = None
    date_from: datetime
    date_to: datetime
    filters_applied: Dict[str, Any] = {}
    total_alerts: int = 0
    total_cases: int = 0
    open_cases: int = 0
    closed_cases: int = 0
    visible_to_customer: bool = False
    status: str
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class CustomerReportListResponse(BaseModel):
    reports: List[CustomerReportResponse]
    total_count: int
    success: bool
    message: str


class CustomerReportVisibilityRequest(BaseModel):
    """Toggle whether an analyst/admin report is shared with the customer portal."""

    visible: bool


class CustomerReportGenerateResponse(BaseModel):
    success: bool
    message: str
    report: Optional[CustomerReportResponse] = None
    error: Optional[str] = None


class CustomerReportGenerateBackgroundResponse(BaseModel):
    success: bool
    message: str
    report_id: int
    report_name: str
    customer_code: str
    status: str
    check_status_url: str
    download_url: str
