import datetime
import secrets
import string
from enum import Enum
from typing import List
from typing import Optional

import bcrypt
import sqlalchemy as sa
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import field_validator
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel

from app.auth.schema.password_policy import PASSWORD_REQUIREMENTS
from app.auth.schema.password_policy import validate_password


class Role(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=256)
    description: str = Field(max_length=256)

    user: Optional["User"] = Relationship(back_populates="role")
    tag_access: List["RoleTagAccess"] = Relationship(back_populates="role")


class UserCustomerAccess(SQLModel, table=True):
    __tablename__ = "user_customer_access"
    id: Optional[int] = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    customer_code: str = Field(foreign_key="customers.customer_code")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    # Relationships
    user: "User" = Relationship(back_populates="customer_access")


class UserTagAccess(SQLModel, table=True):
    """Defines which tags a user can access (allow-list)."""

    __tablename__ = "user_tag_access"
    id: Optional[int] = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    tag_id: int = Field(foreign_key="incident_management_alerttag.id")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    # Relationships
    user: "User" = Relationship(back_populates="tag_access")


class RoleTagAccess(SQLModel, table=True):
    """Defines which tags a role can access (allow-list)."""

    __tablename__ = "role_tag_access"
    id: Optional[int] = Field(primary_key=True)
    role_id: int = Field(foreign_key="role.id")
    tag_id: int = Field(foreign_key="incident_management_alerttag.id")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    # Relationships
    role: "Role" = Relationship(back_populates="tag_access")


class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    username: str = Field(index=True, max_length=256)
    password: str = Field(max_length=256, min_length=6)
    email: EmailStr
    created_at: datetime.datetime = datetime.datetime.now()
    role_id: Optional[int] = Field(foreign_key="role.id")
    # Timestamp of the user's most recent successful login (set on /auth/token,
    # /auth/token/customer-portal and 2FA completion). Surfaced for audit/last-login
    # visibility (issue #943). Nullable: existing users have never logged in under this field.
    last_login_at: Optional[datetime.datetime] = Field(default=None, nullable=True)
    # Set when an admin chose the password (a temporary one emailed, a reset, a new
    # account) and cleared when the user sets their own (#1277). While it is set, a
    # customer_user reaches only the password change (app/auth/services/password_change.py).
    must_change_password: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": sa.false()})

    role: Optional["Role"] = Relationship(back_populates="user")
    customer_access: List["UserCustomerAccess"] = Relationship(back_populates="user")
    tag_access: List["UserTagAccess"] = Relationship(back_populates="user")


# Role ids are fixed: they are stored in user.role_id and role_tag_access.role_id, and
# seeded with these exact ids (db_populate.add_roles_if_not_exist, migration c1219…).
class RoleEnum(int, Enum):
    admin = 1
    analyst = 2
    scheduler = 3
    customer_user = 4
    # An analyst who may also run response actions (quarantine, Velociraptor commands,
    # CoPilot Actions, Sysmon deploy) — only on their assigned customers (#1219).
    responder = 5


# SOC staff scoped to the customers assigned to them: no assignments means no access,
# and they must be created with at least one customer.
CUSTOMER_SCOPED_SOC_ROLES = frozenset({RoleEnum.analyst, RoleEnum.responder})

# Everyone who works in the SOC, as opposed to the scheduler and portal users.
SOC_ROLES = frozenset({RoleEnum.admin, RoleEnum.analyst, RoleEnum.responder})

# A role that extends another gets everything granted to it: a responder is an analyst
# who may also run response actions, so its token carries the analyst scope too and it
# sees the alerts the analyst role's tags open.
ROLE_EXTENDS = {RoleEnum.responder: (RoleEnum.analyst,)}


def effective_roles(role_id: int) -> List[RoleEnum]:
    """The role itself first, then the roles it extends."""
    role = RoleEnum(role_id)
    return [role, *ROLE_EXTENDS.get(role, ())]


class UserInput(SQLModel):
    username: str
    # The password policy (8-72 bytes for bcrypt, the four character classes) lives in
    # schema/password_policy.py, shared with the reset schemas below and both frontends.
    password: str = Field(description=f"Password: {PASSWORD_REQUIREMENTS}")
    email: EmailStr
    role_id: RoleEnum = Field(
        RoleEnum.analyst,
        description="Role ID 1: admin, 2: analyst, 5: responder",
        foreign_key="role.id",
    )

    # The customers an analyst or responder works on: required for those roles (#1219).
    customer_codes: List[str] = Field(default_factory=list, description="Customers to assign: at least one for an analyst or responder")

    @field_validator("password")
    @classmethod
    def check_password(cls, value):
        return validate_password(value)

    @field_validator("role_id")
    @classmethod
    def check_role_id(cls, value):
        if value not in [e.value for e in RoleEnum]:
            raise ValueError("Invalid role ID")
        return value


class UserLogin(SQLModel):
    username: str
    password: str


class Password(BaseModel):
    # Capped at 72 — bcrypt's input limit. The generated chars are ASCII so 72 chars = 72 bytes.
    length: int = Field(
        default=12,
        ge=8,
        le=72,
        description="The length of the password (max 72 — bcrypt input limit)",
    )
    hashed: str  # Holds the hashed password
    plain: str  # Holds the plain password

    @field_validator("length")
    @classmethod
    def validate_length(cls, value):
        if value < 8 or value > 72:
            raise ValueError("Password length must be between 8 and 72 characters.")
        return value

    @classmethod
    def generate(cls, length: int = 12) -> "Password":
        if length < 8 or length > 72:
            raise ValueError("Password length should be between 8 and 72 characters.")

        # Define the characters that can be used in the password
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "@$!%*?&#"

        # Ensure the password has at least one lowercase, one uppercase, one digit, and one special char
        password_chars = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # Fill the rest of the password length with a cryptographically secure random mix
        alphabet = lowercase + uppercase + digits + special
        if length > 4:
            password_chars += [secrets.choice(alphabet) for _ in range(length - 4)]

        # Shuffle using secrets-backed SystemRandom to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)

        # Convert the list of characters into a string
        password = "".join(password_chars)

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # Return the Password object with both the plain and hashed password
        return cls(
            length=length,
            hashed=hashed_password.decode("utf-8"),
            plain=password,
        )


# ! PASSWORD RESET TOKEN GENERATION NOT USING FOR NOW! #
class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetToken(BaseModel):
    username: str
    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value):
        return validate_password(value)


class PasswordReset(BaseModel):
    username: str
    # Optional: when supplied (e.g. customer-portal self-service flow) the route verifies it
    # against the stored hash before changing the password. Admin/analyst reset flows that
    # already prove identity via the JWT may omit it, preserving backwards compatibility.
    current_password: Optional[str] = None
    # Same policy as UserInput. This used to allow only letters, digits and @$!%*?&#, so a
    # password with any other character was refused even though it met every stated rule (#1265).
    new_password: str = Field(description=f"Password: {PASSWORD_REQUIREMENTS}")

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value):
        return validate_password(value)
