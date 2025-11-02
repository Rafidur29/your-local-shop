from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class ReturnRequest(Base):
    __tablename__ = "returns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rma_number = Column(String(32), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(
        String(32), nullable=False, default="REQUESTED"
    )  # REQUESTED, APPROVED, RECEIVED, RECEIVED_PENDING_REFUND, REFUNDED, CANCELLED, FAILED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    data = Column(JSON, nullable=True)

    # relations
    lines = relationship(
        "ReturnLine", back_populates="return_request", cascade="all, delete-orphan"
    )
    credit_note = relationship(
        "CreditNote", back_populates="return_request", uselist=False
    )
