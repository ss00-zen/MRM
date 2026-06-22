import asyncio
from app.models.inventory import ModelInventory
from app.models.audit_log import AuditLog
from app.core.database import engine, Base

async def recreate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(recreate())