from sqlalchemy import Column, String, Float, Boolean, DateTime
from datetime import datetime
from app.core.database import Base
import uuid


class ModelInventory(Base):
    __tablename__ = "model_inventory"

    model_id = Column(String, primary_key=True, index=True)

    # ✅ Core metadata
    model_name = Column(String)
    model_type = Column(String)

    created_by = Column(String)
    model_owner = Column(String)        # ✅ NEW
    business_unit = Column(String)      # ✅ NEW
    data_region = Column(String)

    # ✅ Governance attributes
    risk_tier = Column(String)          # ✅ NEW (High / Medium / Low)
    approval_status = Column(String)

    validation_status = Column(String)

    # ✅ Performance snapshot
    perf_psi = Column(Float, nullable=True)

    # ✅ Regulatory compliance
    sr117_compliant = Column(Boolean, nullable=True)

    # ✅ Lifecycle timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_validated_at = Column(DateTime, nullable=True)   # ✅ NEW
    approval_date = Column(DateTime, nullable=True)       # ✅ NEW


class ModelMetricsHistory(Base):
    __tablename__ = "model_metrics_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String)
    metric_name = Column(String)   # psi, auc, etc
    metric_value = Column(Float)
    source = Column(String)        # monitoring_agent, apigw, etc
    recorded_at = Column(DateTime, default=datetime.utcnow)

