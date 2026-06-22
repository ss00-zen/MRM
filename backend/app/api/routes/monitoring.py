from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.inventory import ModelMetricsHistory

router = APIRouter(prefix="/monitoring")

@router.get("/{model_id}")
async def get_monitoring(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelMetricsHistory)
        .where(ModelMetricsHistory.model_id == model_id)
        .order_by(ModelMetricsHistory.recorded_at.desc())
    )
    return result.scalars().all()
