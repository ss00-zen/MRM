import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.supervisor import SupervisorAgent
from app.core.database import get_db
from app.core.websocket_manager import manager
from app.mcp_clients.sql_mcp_client import SQLMCPClient
from app.models.audit_log import AuditLog
from app.models.inventory import ModelInventory


router = APIRouter(prefix="/onboarding", tags=["Onboarding"])
sql_client = SQLMCPClient()


class ModelOnboardingRequest(BaseModel):
    model_name: str
    model_type: str
    created_by: str
    data_region: str = "US"
    metrics: dict[str, float]


@router.post("/", status_code=201)
async def onboard_model(
    request: ModelOnboardingRequest,
    db: AsyncSession = Depends(get_db),
):
    # ✅ Step 1: Create model inventory row
    model_id = str(uuid.uuid4())

    initial_psi = float(
        request.metrics.get("psi", request.metrics.get("PSI", 0.0))
    )

    model = ModelInventory(
        model_id=model_id,
        model_name=request.model_name,
        model_type=request.model_type,
        created_by=request.created_by,
        model_owner=request.created_by,
        business_unit="Risk",
        data_region=request.data_region,
        risk_tier="Medium",
        approval_status="draft",
        validation_status="draft",
        perf_psi=initial_psi,
        sr117_compliant=False,
    )

    db.add(model)
    await db.commit()
    await db.refresh(model)

    # ✅ Step 2: Insert metrics into history
    for metric_name, metric_value in request.metrics.items():
        await sql_client.insert_metric(
            model_id=model_id,
            metric_name=metric_name,
            value=metric_value,
            source="onboarding",
        )

    # ✅ Step 3: Run Supervisor workflow
    supervisor = SupervisorAgent()

    state = {
        "model_id": model_id,
        "model_metadata": None,
        "validation_status": model.validation_status or "draft",
        "validation_report": None,
        "drift_score": initial_psi,
        "performance_metrics": request.metrics,
        "threshold_breached": False,
        "sr117_compliant": model.sr117_compliant or False,
        "audit_log_entries": [],
        "errors": [],
        "reason": [],
        "data_residency_region": request.data_region,
    }

    state = await supervisor.run(state)

    # ✅ Step 4: Persist updated results
    await db.execute(
        update(ModelInventory)
        .where(ModelInventory.model_id == model_id)
        .values(
            perf_psi=state.get("drift_score", initial_psi),
            validation_status=state.get("validation_status", "draft"),
            sr117_compliant=state.get("sr117_compliant", False),
        )
    )

    # ✅ ✅ IMPORTANT: Add audit log (missing earlier)
    audit = AuditLog(
        model_id=model_id,
        event_type="onboarding_supervisor_run",
        event_payload=state,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(model)

    # ✅ Step 5: Broadcast update
    await manager.broadcast(
        {
            "type": "model_update",
            "model_id": model_id,
        }
    )

    return {
        "model_id": model_id,
        "status": "onboarded",
        "metrics_loaded": list(request.metrics.keys()),
        "validation_status": state.get("validation_status", "draft"),
        "sr117_compliant": state.get("sr117_compliant", False),
        "threshold_breached": state.get("threshold_breached", False),
    }
