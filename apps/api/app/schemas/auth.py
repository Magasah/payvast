import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)
    locale: Literal["tg", "ru"] = "tg"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Plain string: login only looks the email up, format is enforced at registration.
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(BaseModel):
    id: uuid.UUID
    email: str | None
    telegram_username: str | None
    has_telegram: bool
    role: UserRole
    is_admin: bool
    locale: str


class TelegramLoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    init_data: str = Field(min_length=1, max_length=4096)


class LocaleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: Literal["tg", "ru"]


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int
    user: UserOut
