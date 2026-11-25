import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import PaymentMethod, PaymentStatus


class AdminPaymentOut(BaseModel):
    id: uuid.UUID
    user_email: str
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
