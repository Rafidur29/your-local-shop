from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum
from app.db import Base

class IdempotencyStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    operation = Column(String(64), nullable=False)
    status = Column(Enum(IdempotencyStatus), nullable=False, default=IdempotencyStatus.IN_PROGRESS)
    response_body = Column(JSON, nullable=True)
    last_error = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))