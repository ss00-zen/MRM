from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "healthy", "compliance": "SR 11-7 ready"}
