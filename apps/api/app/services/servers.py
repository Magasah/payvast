from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Server, Subscription


async def pick_server(session: AsyncSession, exclude_id: int | None = None) -> Server | None:
    """Least-loaded active server that is not marked as blocked."""
    load = (
        select(Subscription.server_id, func.count().label("n"))
        .group_by(Subscription.server_id)
        .subquery()
    )
    stmt = (
        select(Server)
        .outerjoin(load, load.c.server_id == Server.id)
        .where(Server.is_active.is_(True), Server.is_blocked.is_(False))
        .order_by(func.coalesce(load.c.n, 0), Server.id)
        .limit(1)
    )
    if exclude_id is not None:
        stmt = stmt.where(Server.id != exclude_id)
    return (await session.scalars(stmt)).first()
