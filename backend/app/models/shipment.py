from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db import Base

class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_task_id = Column(Integer, ForeignKey("packing_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    courier = Column(String(64), nullable=False)
    tracking_number = Column(String(128), nullable=False, unique=False)
    status = Column(String(32), nullable=False, default="booked")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    data = Column(JSON, nullable=True)

    # relationship back to packing task
    packing_task = relationship("PackingTask", back_populates="shipment")