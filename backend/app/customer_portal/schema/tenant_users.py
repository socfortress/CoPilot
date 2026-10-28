"""A customer admin's view of their customers' portal users (#1296): ``/customer_portal/users``."""

import datetime
import re
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator

from app.customer_portal.schema.me import PortalCustomer

# What a new portal username may be: a letter or digit, then letters, digits and ._@-, 3 to 64
# characters. Stricter than the SOC's own form on purpose: it is typed by a customer.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{2,63}$")
USERNAME_RULE = "3 to 64 characters: letters, digits and . _ @ -, starting with a letter or a digit"


class TenantUser(BaseModel):
    """A portal user as their customer admin sees them.

    ``customers`` lists only the customers the caller administers: another customer the user
    also belongs to is never named, only reflected in ``can_manage`` and ``managed_by_soc_reason``.
    """

    id: int
    username: str
    email: str
    customers: List[PortalCustomer]
    is_customer_admin: bool
    # May only read their (administered) customers' data (#1312).
    read_only: bool = False
    disabled: bool
    disabled_at: Optional[datetime.datetime] = None
    must_change_password: bool
    totp_enabled: bool
    last_login_at: Optional[datetime.datetime] = None
    is_self: bool
    # Whether the caller may disable, enable, reset 2FA or issue a temporary password for them.
    can_manage: bool
    # Why not, when they may not: the caller themself, another customer admin, or an account
    # that also belongs to a customer the caller does not administer.
    managed_by_soc_reason: Optional[str] = None


class TenantUsersResponse(BaseModel):
    success: bool = True
    message: str = "Users retrieved successfully"
    # The customers the caller administers, the choices for an invitation.
    customers: List[PortalCustomer]
    users: List[TenantUser]
    # Whether a temporary password can go by email; when it cannot, it is shown once instead.
    smtp_configured: bool


class InviteRequest(BaseModel):
    username: str = Field(description=f"Username: {USERNAME_RULE}")
    email: EmailStr
    customer_codes: List[str] = Field(min_length=1, description="Customers the user may see: at least one the caller administers")
    # The new user may only read those customers' data (#1312).
    read_only: bool = False

    @field_validator("username")
    @classmethod
    def check_username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.match(value):
            raise ValueError(f"Username must be {USERNAME_RULE}")
        return value

    @field_validator("customer_codes")
    @classmethod
    def unique_codes(cls, value: List[str]) -> List[str]:
        return list(dict.fromkeys(code.strip() for code in value if code.strip()))


class ReadOnlyRequest(BaseModel):
    """Let a portal user only read their customers' data, or change it again (#1312)."""

    read_only: bool


Delivery = Literal["email", "shown"]


class TemporaryPassword(BaseModel):
    """How a temporary password reached its user.

    ``email``: sent, and never in this response. ``shown``: SMTP is not configured, or the email
    could not be rendered or sent (``email_problem`` says which), so ``temporary_password`` is in
    this response, the only time it is ever returned: the caller hands it over themself.
    """

    delivery: Delivery
    temporary_password: Optional[str] = None
    email_problem: Optional[str] = None


class InviteResponse(TemporaryPassword):
    success: bool = True
    message: str
    user: TenantUser


class TenantUserActionResponse(BaseModel):
    success: bool = True
    message: str
    user: TenantUser


class TemporaryPasswordResponse(TemporaryPassword):
    success: bool = True
    message: str
    user: TenantUser
