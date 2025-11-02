from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class PackingTask(Base):
    __tablename__ = "packing_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(
        String(32), nullable=False, default="pending"
    )  # pending, packed, error
    assigned_to = Column(String(128), nullable=True)  # optional admin user
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # relationship (useful for admin UI)
    order = relationship("Order", backref="packing_tasks")
    shipment = relationship("Shipment", back_populates="packing_task", uselist=False)
