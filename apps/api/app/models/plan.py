from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin


class Plan(TimestampMixin, Base):
    """Tariff. Price is stored as an integer in dirams (1 somoni = 100 dirams), never float."""

    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("price_dirams > 0", name="price_positive"),
        CheckConstraint("duration_days > 0", name="duration_positive"),
        CheckConstraint("device_limit > 0", name="device_limit_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_tg: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    price_dirams: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    device_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
