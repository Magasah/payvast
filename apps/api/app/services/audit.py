from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, User


def audit(
    session: AsyncSession,
    admin: User,
    action: str,
    target_type: str,
    target_id: object,
    **details: Any,
) -> None:
    """Add an audit entry to the CURRENT transaction: it commits or rolls back with the action."""
    session.add(
        AdminAuditLog(
            admin_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=details,
        )
    )
