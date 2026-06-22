import asyncio
import uuid

from app.core.database import SessionLocal
from app.models.inventory import ModelInventory


async def main():
    async with SessionLocal() as db:
        model = ModelInventory(
            model_id=str(uuid.uuid4()),
            model_name="Credit Risk Model",
            model_type="credit_risk",
            approval_status="approved",
            created_by="user123",
            perf_auc=0.82,
            perf_psi=0.05,
            perf_ks=0.61,
            data_region="US"
        )

        db.add(model)
        await db.commit()

asyncio.run(main())