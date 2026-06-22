from fastapi import APIRouter
from app.validators.audit_codes import AUDIT_CODES

router = APIRouter(prefix="/audit")

@router.get("/codes")
async def get_audit_codes():
    return AUDIT_CODES