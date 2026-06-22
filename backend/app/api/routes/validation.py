from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.validation import ValidationRecord
from sqlalchemy import select

router = APIRouter(prefix="/validation")

@router.get("/{model_id}")
async def get_validation(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ValidationRecord).where(ValidationRecord.model_id == model_id)
    )
    return result.scalar_one_or_none()