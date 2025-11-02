from datetime import datetime, timezone

from app.db import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(64), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    reserved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reserved_until = Column(DateTime, nullable=True)
    status = Column(
        String(32), nullable=False, default="reserved"
    )  # reserved, committed, released, expired
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)

    def is_active(self, now=None):
        if not now:
            now = datetime.now(timezone.utc)
        return self.status == "reserved" and (
            self.reserved_until is None or self.reserved_until > now
        )
