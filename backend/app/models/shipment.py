from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db import Base

class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_task_id = Column(Integer, ForeignKey("packing_tasks.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    courier = Column(String(64), nullable=False)
    tracking_number = Column(String(128), nullable=False, unique=True)
    status = Column(String(32), nullable=False, default="booked")  # booked, picked_up, in_transit, delivered, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    data = Column(JSON, nullable=True)

    packing_task = relationship("PackingTask", back_populates="shipment")
