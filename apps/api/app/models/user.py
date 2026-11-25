import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin
from app.models.enums import UserRole


class User(TimestampMixin, Base):
    """Minimal personal data. No IPs, no real names.

    A user signs in either with email + password or through Telegram (WebApp initData).
    The admin role is only valid together with a telegram_id listed in ADMIN_TELEGRAM_IDS.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR telegram_id IS NOT NULL", name="has_identity"),
        CheckConstraint("(email IS NULL) = (password_hash IS NULL)", name="email_has_password"),
        CheckConstraint("role <> 'admin' OR telegram_id IS NOT NULL", name="admin_has_telegram"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(2), default="tg", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Bumped on logout / password change: every older refresh token becomes invalid.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Per-account brute-force protection (in addition to per-IP rate limits).
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    login_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
