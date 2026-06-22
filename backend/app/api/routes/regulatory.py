from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.mcp_clients.sql_mcp_client import SQLMCPClient

router = APIRouter(prefix="/regulatory")
sql_client = SQLMCPClient()

@router.get("/reports")
async def get_regulatory_reports(db: AsyncSession = Depends(get_db)):
    return await sql_client.generate_sr11_report()
