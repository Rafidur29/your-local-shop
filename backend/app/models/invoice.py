from datetime import datetime, timezone

from app.db import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    invoice_no = Column(String(32), unique=True, nullable=False)
    total_cents = Column(Integer, nullable=False)
    tax_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    data = Column(JSON, nullable=True)

    # relationship back to Order
    order = relationship("Order", back_populates="invoice")
