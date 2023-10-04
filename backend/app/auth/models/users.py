import datetime
from typing import Optional

from pydantic import validator, EmailStr
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    username: str = Field(index=True)
    password: str = Field(max_length=256, min_length=6)
    email: EmailStr
    created_at: datetime.datetime = datetime.datetime.now()
    is_admin: bool = False

    smtp: "SMTP" = Relationship(back_populates="user")


class UserInput(SQLModel):
    username: str
    password: str = Field(max_length=256, min_length=6)
    password2: str
    email: EmailStr
    is_admin: bool = False

    @validator('password2')
    def password_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('passwords don\'t match')
        return v


class UserLogin(SQLModel):
    email: str
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

    @validator('smtp_password2')
    def password_match(cls, v, values, **kwargs):
        if 'smtp_password' in values and v != values['smtp_password']:
            raise ValueError('passwords don\'t match')
        return v
