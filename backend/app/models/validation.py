from sqlalchemy import Column, String, DateTime
from datetime import datetime
import uuid

from app.core.database import Base


class ValidationRecord(Base):
    __tablename__ = "validation_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = Column(String, index=True)

    # lifecycle states: intake -> testing -> docs_review -> approval
    stage = Column(String, default="intake")

    # status examples: pending / approved / rejected / in_review
    status = Column(String, default="pending")

    # external workflow references
    jira_ticket_id = Column(String, nullable=True)

    # links / pointers to stored artifacts
    validation_report_ref = Column(String, nullable=True)
    assumptions_log_ref = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
