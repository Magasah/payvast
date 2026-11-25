"""telegram login, admin bound to telegram id, card payments, login lockout

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Admin now requires a Telegram id from ADMIN_TELEGRAM_IDS: old email admins lose the role.
    op.execute("UPDATE users SET role = 'user' WHERE role = 'admin'")

    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.String(32), nullable=True))
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users", sa.Column("login_locked_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_unique_constraint(op.f("uq_users_telegram_id"), "users", ["telegram_id"])
    op.alter_column("users", "email", existing_type=sa.String(254), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.create_check_constraint(
        op.f("ck_users_has_identity"), "users", "email IS NOT NULL OR telegram_id IS NOT NULL"
    )
    op.create_check_constraint(
        op.f("ck_users_email_has_password"), "users", "(email IS NULL) = (password_hash IS NULL)"
    )
    op.create_check_constraint(
        op.f("ck_users_admin_has_telegram"), "users", "role <> 'admin' OR telegram_id IS NOT NULL"
    )

    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'card'")


def downgrade() -> None:
    # Postgres cannot drop an enum value; 'card' stays in payment_method.
    op.drop_constraint(op.f("ck_users_admin_has_telegram"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_email_has_password"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_has_identity"), "users", type_="check")
    op.execute("DELETE FROM users WHERE email IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(254), nullable=False)
    op.drop_constraint(op.f("uq_users_telegram_id"), "users", type_="unique")
    op.drop_column("users", "login_locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_id")
