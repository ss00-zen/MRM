from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.websocket_manager import manager
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.inventory import ModelInventory, ModelMetricsHistory
from app.models.jira_incident import JiraIncident
from app.agents.supervisor import SupervisorAgent
from app.mcp_clients.sql_mcp_client import SQLMCPClient

router = APIRouter(prefix="/models", tags=["Model Management"])
sql_client = SQLMCPClient()


class MetricRequest(BaseModel):
    metric_name: str
    metric_value: float


# ✅ Insert metric
@router.post("/{model_id}/metrics")
@router.post("/{model_id}/metrics")
async def insert_metric(
    model_id: str,
    request: MetricRequest,
    db: AsyncSession = Depends(get_db)
):
    model = await db.get(ModelInventory, model_id)

    if not model:
        return {"error": "Model not found"}

    # ✅ Insert metric into history
    await sql_client.insert_metric(
        model_id=model_id,
        metric_name=request.metric_name,
        value=request.metric_value,
        source="ingestion"
    )

    # ✅ Update latest PSI in inventory
    if request.metric_name.lower() == "psi":
        await db.execute(
            update(ModelInventory)
            .where(ModelInventory.model_id == model_id)
            .values(perf_psi=request.metric_value)
        )

        await db.commit()

        # ✅ ✅ 🔥 CRITICAL FIX: RUN SUPERVISOR
        from app.agents.supervisor import SupervisorAgent

        supervisor = SupervisorAgent()

        state = {
            "model_id": model_id,
            "validation_status": model.validation_status or "draft",
            "drift_score": request.metric_value,
            "performance_metrics": {"psi": request.metric_value},
            "threshold_breached": False,
            "sr117_compliant": model.sr117_compliant or False,
            "errors": [],
            "reason": []
        }

        state = await supervisor.run(state)

        # ✅ Persist updated results
        await db.execute(
            update(ModelInventory)
            .where(ModelInventory.model_id == model_id)
            .values(
                perf_psi=state.get("drift_score"),
                validation_status=state.get("validation_status"),
                sr117_compliant=state.get("sr117_compliant")
            )
        )

        await db.commit()

        # ✅ Broadcast UI update
        await manager.broadcast({
            "type": "model_update",
            "model_id": model_id
        })

    return {"message": "metric inserted"}



# ✅ Get metrics
@router.get("/{model_id}/metrics")
async def get_metrics(model_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelMetricsHistory)
        .where(ModelMetricsHistory.model_id == model_id)
    )

    rows = result.scalars().all()

    return [
        {
            "metric_name": r.metric_name,
            "metric_value": r.metric_value,
            "time": str(r.recorded_at)
        }
        for r in rows
    ]


# ✅ Monitor
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
        "reason": []
    }

    state = await supervisor.run(state)

    await db.execute(
        update(ModelInventory)
        .where(ModelInventory.model_id == model_id)
        .values(
            perf_psi=state.get("drift_score"),
            validation_status=state.get("validation_status"),
            sr117_compliant=state.get("sr117_compliant")
        )
    )

    audit = AuditLog(
        model_id=model_id,
        event_type="monitoring_run",
        event_payload=state
    )

    db.add(audit)
    await db.commit()

    print("📡 Broadcast (monitor update):", model_id)  # DEBUG
    await manager.broadcast({
        "type": "model_update",
        "model_id": model_id
    })

    return state


# ✅ List models
@router.get("/")
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ModelInventory))
    models = result.scalars().all()

    response = []

    for m in models:
        inc_result = await db.execute(
            select(JiraIncident).where(JiraIncident.model_id == m.model_id)
        )
        incidents = inc_result.scalars().all()

        latest_status = None
        if incidents:
            latest = sorted(incidents, key=lambda x: x.created_at, reverse=True)[0]
            latest_status = latest.status

        has_open = any(i.status != "approval" for i in incidents)

        response.append({
            "model_id": m.model_id,
            "model_name": m.model_name,
            "model_type": m.model_type,
            "perf_psi": m.perf_psi,
            "validation_status": latest_status or "NA",
            "has_open_incidents": has_open,
            "sr117_compliant": m.sr117_compliant
        })

    return response


# ✅ Get model
@router.get("/{model_id}")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelInventory, model_id)

    if not model:
        return {"error": "Model not found"}

    return {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "model_type": model.model_type,
        "validation_status": model.validation_status,
        "perf_psi": model.perf_psi,
        "sr117_compliant": model.sr117_compliant
    }