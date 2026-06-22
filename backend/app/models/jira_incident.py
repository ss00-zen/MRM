from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class JiraIncident(Base):
    __tablename__ = "jira_incidents"

    ticket_key = Column(String, primary_key=True, index=True)
    model_id = Column(String, nullable=False, index=True)
    validation_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="intake")
    summary = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())