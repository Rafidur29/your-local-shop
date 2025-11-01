from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db import Base

class CreditNote(Base):
    __tablename__ = "credit_notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    credit_no = Column(String(32), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    return_id = Column(Integer, ForeignKey("returns.id"), nullable=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    tax_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    data = Column(JSON, nullable=True)

    return_request = relationship("ReturnRequest", back_populates="credit_note")
