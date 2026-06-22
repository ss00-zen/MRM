from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.models.jira_incident import JiraIncident

router = APIRouter(prefix="/jira", tags=["Dummy Jira"])

VALID_STAGES = ["intake", "draft", "testing", "docs_review", "approval"]


def generate_ticket_key() -> str:
    return f"VAL-{str(uuid.uuid4())[:8].upper()}"


@router.post("/incidents")
async def create_incident(payload: dict, db: AsyncSession = Depends(get_db)):
    model_id = payload.get("model_id")
    validation_type = payload.get("validation_type", "drift_incident")

    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    ticket = JiraIncident(
        ticket_key=generate_ticket_key(),
        model_id=model_id,
        validation_type=validation_type,
        status="intake",
        summary=f"Validation for model {model_id}",
    )

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return {
        "key": ticket.ticket_key,
        "model_id": ticket.model_id,
        "validation_type": ticket.validation_type,
        "status": ticket.status,
        "created_at": str(ticket.created_at),
    }


@router.get("/incidents/{ticket_key}")
async def get_incident(ticket_key: str, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(JiraIncident, ticket_key)

    if not ticket:
        raise HTTPException(status_code=404, detail="Incident not found")

    return {
        "key": ticket.ticket_key,
        "model_id": ticket.model_id,
        "validation_type": ticket.validation_type,
        "status": ticket.status,
        "created_at": str(ticket.created_at),
    }


@router.get("/incidents/by-model/{model_id}")
async def get_incident_by_model(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JiraIncident)
        .where(JiraIncident.model_id == model_id)
        .order_by(JiraIncident.created_at.desc())
    )
    ticket = result.scalars().first()

    if not ticket:
        return []  # Return empty list if no incidents found for the model

    return {
        "key": ticket.ticket_key,
        "model_id": ticket.model_id,
        "validation_type": ticket.validation_type,
        "status": ticket.status,
        "created_at": str(ticket.created_at),
    }


# ✅ CRITICAL FIX:
# for a brand-new model with no incidents, return [] and 200 — NOT 404
@router.get("/incidents/by-model-all/{model_id}")
async def get_all_incidents(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JiraIncident)
        .where(JiraIncident.model_id == model_id)
        .order_by(JiraIncident.created_at.desc())
    )
    rows = result.scalars().all()

    return [
        {
            "key": r.ticket_key,
            "model_id": r.model_id,
            "validation_type": r.validation_type,
            "status": r.status,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


@router.post("/incidents/{ticket_key}/transition")
async def transition_incident(ticket_key: str, payload: dict, db: AsyncSession = Depends(get_db)):
    new_status = payload.get("status")

    if new_status not in VALID_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {VALID_STAGES}",
        )

    ticket = await db.get(JiraIncident, ticket_key)
    if not ticket:
        raise HTTPException(status_code=404, detail="Incident not found")

    ticket.status = new_status
    await db.commit()
    await db.refresh(ticket)

    return {
        "key": ticket.ticket_key,
        "model_id": ticket.model_id,
        "status": ticket.status,
        "created_at": str(ticket.created_at),
    }