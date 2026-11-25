import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import PaymentMethod, PaymentStatus, SubscriptionStatus


class AdminPaymentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None
    user_telegram: str | None
    plan_code: str
    method: PaymentMethod
    amount_dirams: int
    duration_days: int
    status: PaymentStatus
    has_receipt: bool
    created_at: datetime
    reviewed_at: datetime | None
    reject_reason: str | None


class RejectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class ServerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    host: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9.-]+$")
    country: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    panel_inbound_id: int | None = Field(default=None, gt=0)


class ServerPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    is_blocked: bool | None = None
    panel_inbound_id: int | None = Field(default=None, gt=0)


class ServerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host: str
    country: str
    panel_inbound_id: int | None
    is_active: bool
    is_blocked: bool


class MoveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server_id: int | None = Field(default=None, gt=0)


class AdminSubscriptionOut(BaseModel):
    id: uuid.UUID
    status: SubscriptionStatus
    expires_at: datetime
    days_left: int
    device_limit: int
    server_id: int | None
    subscription_url: str


class AdminUserRow(BaseModel):
    id: uuid.UUID
    email: str | None
    telegram_id: int | None
    telegram_username: str | None
    is_admin: bool
    is_active: bool
    locale: str
    created_at: datetime
    subscription_status: SubscriptionStatus | None
    expires_at: datetime | None


class AdminUserPage(BaseModel):
    items: list[AdminUserRow]
    total: int


class AdminUserDetail(BaseModel):
    user: AdminUserRow
    subscription: AdminSubscriptionOut | None
    payments: list[AdminPaymentOut]


class AdjustDaysIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days: int = Field(ge=-3650, le=3650)
    device_limit: int | None = Field(default=None, ge=1, le=10)
    note: str | None = Field(default=None, max_length=300)


class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=300)


class UserActiveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class AuditOut(BaseModel):
    id: int
    created_at: datetime
    admin: str | None
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any]


class AuditPage(BaseModel):
    items: list[AuditOut]
    next_before: int | None
