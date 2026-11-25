import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import PaymentMethod, PaymentStatus


class PaymentCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: int = Field(gt=0)
    method: PaymentMethod


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: int
    method: PaymentMethod
    amount_dirams: int
    duration_days: int
    status: PaymentStatus
    has_receipt: bool
    reject_reason: str | None
    created_at: datetime
    confirmed_at: datetime | None


class PaymentMethodOut(BaseModel):
    method: PaymentMethod
    wallet: str
