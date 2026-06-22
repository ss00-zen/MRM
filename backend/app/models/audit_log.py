from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
import uuid

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    # ✅ Unique identifier
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ✅ Which model this belongs to
    model_id = Column(String, index=True)

    # ✅ What happened (structured)
    event_type = Column(String)  
    # e.g. "model_created", "monitoring_run", "validation", "incident_triggered"

    # ✅ Full structured payload
    event_payload = Column(JSON)
    """
    Example:
    {
        "drift_score": 0.18,
        "threshold_breached": true,
        "validation_status": "in_validation",
        "reason": [...]
    }
    """

    # ✅ Who triggered (future RLS support)
    triggered_by = Column(String, nullable=True)

    # ✅ Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
