from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, update
from app.core.database import SessionLocal
from app.models.inventory import ModelInventory, ModelMetricsHistory
from app.models.audit_log import AuditLog
from app.models.validation import ValidationRecord

# ✅ Create FastMCP Server
mcp = FastMCP("MRM-SQL-Server")

@mcp.tool()
async def query_model_inventory(model_id: str):
    """Fetch full model metadata from the inventory."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(ModelInventory).where(ModelInventory.model_id == model_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        
        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "model_owner": model.model_owner,
            "business_unit": model.business_unit,
            "data_region": model.data_region,
            "risk_tier": model.risk_tier,
            "approval_status": model.approval_status,
            "validation_status": model.validation_status,
            "perf_psi": model.perf_psi,
            "sr117_compliant": model.sr117_compliant
        }

@mcp.tool()
async def get_all_latest_metrics(model_id: str):
    """Get the most recent value for each unique metric for a model."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(ModelMetricsHistory)
            .where(ModelMetricsHistory.model_id == model_id)
            .order_by(ModelMetricsHistory.recorded_at.desc())
        )
        rows = result.scalars().all()
        
        metrics = {}
        for r in rows:
            if r.metric_name not in metrics:
                metrics[r.metric_name] = r.metric_value
        return metrics

@mcp.tool()
async def get_metrics_history(model_id: str):
    """Retrieve the full history of metrics for a model."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(ModelMetricsHistory)
            .where(ModelMetricsHistory.model_id == model_id)
            .order_by(ModelMetricsHistory.recorded_at.desc())
        )
        rows = result.scalars().all()
        return [
            {"metric_name": r.metric_name, "metric_value": r.metric_value, "timestamp": str(r.recorded_at)}
            for r in rows
        ]

@mcp.tool()
async def insert_metric(model_id: str, metric_name: str, metric_value: float, source: str = "mcp"):
    """Record a new performance metric."""
    async with SessionLocal() as db:
        metric = ModelMetricsHistory(
            model_id=model_id,
            metric_name=metric_name,
            metric_value=metric_value,
            source=source
        )
        db.add(metric)
        await db.commit()
    return {"status": "success"}

@mcp.tool()
async def get_audit_logs(model_id: str):
    """Fetch the audit trail for a model."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(AuditLog).where(AuditLog.model_id == model_id).order_by(AuditLog.created_at.desc())
        )
        logs = result.scalars().all()
        return [{"event": l.event_type, "timestamp": str(l.created_at)} for l in logs]

@mcp.tool()
async def get_validation_record(model_id: str):
    """Fetch validation records (Stub)."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(ValidationRecord).where(ValidationRecord.model_id == model_id)
        )
        record = result.scalar_one_or_none()
        return record.__dict__ if record else None

@mcp.tool()
async def update_validation_record(record: dict):
    """Update validation records (Stub)."""
    return {"status": "updated_stub"}

@mcp.tool()
async def generate_sr11_report(model_id: str):
    """Generate SR 11-7 compliance report (Stub)."""
    return {"status": "generated", "report_url": f"/reports/SR117_{model_id}.pdf"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=9000, path="/mcp")
