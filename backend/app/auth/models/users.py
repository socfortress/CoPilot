import datetime
from enum import Enum
from typing import Optional

from pydantic import EmailStr
from pydantic import validator
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class Role(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=256)
    description: str = Field(max_length=256)

    user: Optional["User"] = Relationship(back_populates="role")


class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    username: str = Field(index=True)
    password: str = Field(max_length=256, min_length=6)
    email: EmailStr
    created_at: datetime.datetime = datetime.datetime.now()
    role_id: Optional[int] = Field(foreign_key="role.id")

    smtp: "SMTP" = Relationship(back_populates="user")
    role: Optional["Role"] = Relationship(back_populates="user")


# Enum class for role_id 1,2,3
class RoleEnum(int, Enum):
    admin = 1
    analyst = 2


class UserInput(SQLModel):
    username: str
    password: str = Field(
        max_length=256,
        min_length=8,
        regex="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$",
        description="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number",
    )
    email: EmailStr
    role_id: RoleEnum = Field(RoleEnum.analyst, description="Role ID 1: admin, 2: analyst", foreign_key="role.id")


class UserLogin(SQLModel):
    username: str
    password: str


class SMTP(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    email: EmailStr
    smtp_password: str = Field(max_length=256)
    smtp_server: str = Field(max_length=256)
    smtp_port: int
    user_id: int = Field(foreign_key="user.id")

    user: "User" = Relationship(back_populates="smtp")


class SMTPInput(SQLModel):
    email: EmailStr
    smtp_password: str = Field(max_length=256)
    smtp_password2: str = Field(max_length=256)
    smtp_server: str = Field(max_length=256)
    smtp_port: int

    @validator("smtp_password2")
    def password_match(cls, v, values, **kwargs):
        if "smtp_password" in values and v != values["smtp_password"]:
            raise ValueError("passwords don't match")
        return v
