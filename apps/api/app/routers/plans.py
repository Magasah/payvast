from fastapi import APIRouter
from sqlalchemy import select

from app.deps import SessionDep
from app.models import Plan
from app.schemas.plan import PlanOut

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=list[PlanOut])
async def list_plans(session: SessionDep) -> list[PlanOut]:
    rows = await session.scalars(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order, Plan.id)
    )
    return [PlanOut.model_validate(p) for p in rows]
