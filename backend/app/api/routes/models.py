from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.supervisor import SupervisorAgent
from app.core.database import get_db
from app.core.websocket_manager import manager
from app.mcp_clients.sql_mcp_client import SQLMCPClient
from app.models.audit_log import AuditLog
from app.models.inventory import ModelInventory, ModelMetricsHistory
from app.models.jira_incident import JiraIncident


router = APIRouter(prefix="/models", tags=["Model Management"])
sql_client = SQLMCPClient()


class MetricRequest(BaseModel):
    metric_name: str
    metric_value: float


# ✅ Insert metric
@router.post("/{model_id}/metrics")
async def insert_metric(model_id: str, request: MetricRequest, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelInventory, model_id)

    if not model:
        return {"error": "Model not found"}

    await sql_client.insert_metric(
        model_id=model_id,
        metric_name=request.metric_name,
        value=request.metric_value,
        source="ingestion",
    )

    if request.metric_name.lower() == "psi":
        await db.execute(
            update(ModelInventory)
            .where(ModelInventory.model_id == model_id)
            .values(perf_psi=request.metric_value)
        )
        await db.commit()

        supervisor = SupervisorAgent()

        state = {
            "model_id": model_id,
            "validation_status": model.validation_status or "draft",
            "drift_score": request.metric_value,
            "performance_metrics": {"psi": request.metric_value},
            "threshold_breached": False,
            "sr117_compliant": model.sr117_compliant or False,
            "audit_log_entries": [],
            "errors": [],
            "reason": [],
        }

        state = await supervisor.run(state)

        await db.execute(
            update(ModelInventory)
            .where(ModelInventory.model_id == model_id)
            .values(
                perf_psi=state.get("drift_score"),
                validation_status=state.get("validation_status"),
                sr117_compliant=state.get("sr117_compliant"),
            )
        )

        db.add(AuditLog(
            model_id=model_id,
            event_type="metric_ingestion_supervisor_run",
            event_payload=state,
        ))

        await db.commit()

        await manager.broadcast({
            "type": "model_update",
            "model_id": model_id,
        })

    return {"message": "metric inserted"}


# ✅ Get metrics
@router.get("/{model_id}/metrics")
async def get_metrics(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelMetricsHistory)
        .where(ModelMetricsHistory.model_id == model_id)
        .order_by(ModelMetricsHistory.recorded_at.desc())
    )

    rows = result.scalars().all()

    return [
        {
            "metric_name": row.metric_name,
            "metric_value": row.metric_value,
            "time": str(row.recorded_at),
        }
        for row in rows
    ]


# ✅ Monitor trigger
@router.post("/{model_id}/monitor")
async def run_monitor(model_id: str, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelInventory, model_id)

    if not model:
        return {"error": "Model not found"}

    supervisor = SupervisorAgent()

    state = {
        "model_id": model_id,
        "validation_status": model.validation_status or "draft",
        "drift_score": model.perf_psi or 0.0,
        "performance_metrics": {},
        "threshold_breached": False,
        "sr117_compliant": model.sr117_compliant or False,
        "audit_log_entries": [],
        "errors": [],
        "reason": [],
        "force_monitoring": True,
    }

    state = await supervisor.run(state)

    await db.execute(
        update(ModelInventory)
        .where(ModelInventory.model_id == model_id)
        .values(
            perf_psi=state.get("drift_score"),
            validation_status=state.get("validation_status"),
            sr117_compliant=state.get("sr117_compliant"),
        )
    )

    db.add(AuditLog(
        model_id=model_id,
        event_type="monitoring_run",
        event_payload=state,
    ))

    await db.commit()

    await manager.broadcast({
        "type": "model_update",
        "model_id": model_id,
    })

    return state


# ✅ Dashboard list (FIXED N+1)
@router.get("/")
async def list_models(db: AsyncSession = Depends(get_db)):
    # ✅ fetch all models
    result = await db.execute(select(ModelInventory))
    models = result.scalars().all()

    # ✅ ✅ fetch ALL incidents in ONE query
    inc_result = await db.execute(select(JiraIncident))
    all_incidents = inc_result.scalars().all()

    # ✅ group incidents by model_id
    incident_map = {}
    for inc in all_incidents:
        incident_map.setdefault(inc.model_id, []).append(inc)

    response = []

    for model in models:
        incidents = incident_map.get(model.model_id, [])

        has_open_incidents = any(
            inc.status != "approval"
            for inc in incidents
        )

        response.append({
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "perf_psi": model.perf_psi,
            "validation_status": (
                "Active Tickets" if has_open_incidents else "No Active Tickets"
            ),
            "has_open_incidents": has_open_incidents,
            "sr117_compliant": model.sr117_compliant,
        })

    return response


# ✅ Model detail (FIXED explanation source)
@router.get("/{model_id}")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelInventory, model_id)

    if not model:
        return {"error": "Model not found"}

    # ✅ incidents
    incidents = (await db.execute(
        select(JiraIncident)
        .where(JiraIncident.model_id == model_id)
        .order_by(JiraIncident.created_at.desc())
    )).scalars().all()

    # ✅ latest audit (for explanations)
    audit = (await db.execute(
        select(AuditLog)
        .where(AuditLog.model_id == model_id)
        .order_by(desc(AuditLog.created_at))
    )).scalars().first()

    explanations = {}
    if audit and audit.event_payload:
        explanations = audit.event_payload.get("agent_explanations", {})

    return {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "model_type": model.model_type,
        "perf_psi": model.perf_psi,
        "sr117_compliant": model.sr117_compliant,

        # ✅ FIXED
        "monitoring_explanation": explanations.get("monitoring"),
        "regulatory_explanation": explanations.get("regulatory"),

        "incidents": [
            {
                "key": inc.ticket_key,
                "status": inc.status,
                "validation_type": inc.validation_type,
                "created_at": str(inc.created_at),
            }
            for inc in incidents
        ],
    }
