import datetime
import random
import re
import string
from enum import Enum
from typing import Optional

import bcrypt
from pydantic import BaseModel
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
    username: str = Field(index=True, max_length=256)
    password: str = Field(max_length=256, min_length=6)
    email: EmailStr
    created_at: datetime.datetime = datetime.datetime.now()
    role_id: Optional[int] = Field(foreign_key="role.id")

    smtp: "SMTP" = Relationship(back_populates="user")
    role: Optional["Role"] = Relationship(back_populates="user")


# Enum class for role_id 1,2
class RoleEnum(int, Enum):
    admin = 1
    analyst = 2
    scheduler = 3


class UserInput(SQLModel):
    username: str
    password: str = Field(
        max_length=256,
        min_length=8,
        regex="^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&#]).{8,}$",
        description="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character",
    )
    email: EmailStr
    role_id: RoleEnum = Field(
        RoleEnum.analyst,
        description="Role ID 1: admin, 2: analyst",
        foreign_key="role.id",
    )

    @validator("role_id")
    def check_role_id(cls, value):
        if value not in [e.value for e in RoleEnum]:
            raise ValueError("Invalid role ID")
        return value


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


class Password(BaseModel):
    length: int = Field(
        default=12,
        ge=8,
        le=128,
        description="The length of the password",
    )
    hashed: str  # Holds the hashed password
    plain: str  # Holds the plain password

    @validator("length")
    def validate_length(cls, value):
        if value < 8 or value > 128:
            raise ValueError("Password length must be between 8 and 128 characters.")
        return value

    @classmethod
    def generate(cls, length: int = 12) -> "Password":
        if length < 8:  # Ensure the password is a reasonable length
            raise ValueError("Password length should be at least 8 characters.")

        # Define the characters that can be used in the password
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits

        # Ensure the password has at least one lowercase, one uppercase, one digit, and one symbol
        password_chars = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
        ]

        # Fill the rest of the password length with a random mix of characters
        if length > 4:
            password_chars += random.choices(
                lowercase + uppercase + digits,
                k=length - 4,
            )

        # Shuffle the resulting password list to avoid predictable patterns
        random.shuffle(password_chars)

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

    @validator("new_password")
    def validate_password(cls, password):
        if len(password) < 8 or len(password) > 256:
            raise ValueError("Password length must be between 8 and 256 characters.")
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[@$!%*?&#]", password):
            raise ValueError("Password must contain at least one special character.")
        return password


class PasswordReset(BaseModel):
    username: str
    new_password: str = Field(
        max_length=256,
        min_length=8,
        regex="^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&#])[A-Za-z\\d@$!%*?&#]{8,}$",
        description="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character",
    )
