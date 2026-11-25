import uuid

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin
from app.models.enums import UserRole


class User(TimestampMixin, Base):
    """Minimal personal data: email, password hash, role, UI language. No IPs, no names."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(2), default="tg", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Bumped on logout / password change: every older refresh token becomes invalid.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
