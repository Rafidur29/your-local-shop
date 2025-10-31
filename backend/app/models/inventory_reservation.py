from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from app.db import Base
from datetime import datetime, timezone

class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    reserved_at = Column(DateTime(timezone=True), server_default=func.now())
    reserved_until = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="reserved")  # reserved, released, committed, expired
    order_id = Column(Integer, nullable=True, index=True)  # optional link when committed

    def is_active(self, now=None):
        if not now:
            now = datetime.now(timezone.utc)
        return self.status == "reserved" and (self.reserved_until is None or self.reserved_until > now)
