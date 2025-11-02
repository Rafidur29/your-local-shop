from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import select, update
from ..models import ProductVariant, InventoryReservation


RESERVATION_TTL_MIN = 15


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def _expire_old(self):
        now = datetime.utcnow()
        self.db.query(InventoryReservation).filter(
            InventoryReservation.status == "ACTIVE",
            InventoryReservation.reserved_until < now,
        ).update({InventoryReservation.status: "EXPIRED"})
        self.db.commit()

    def available_stock(self, sku: str) -> int:
        self._expire_old()
        pv = (
            self.db.execute(select(ProductVariant).where(ProductVariant.sku == sku))
            .scalar_one()
        )
        active_reserved = (
            self.db.query(InventoryReservation)
            .filter(
                InventoryReservation.sku == sku,
                InventoryReservation.status == "ACTIVE",
            )
            .with_entities(InventoryReservation.qty)
            .all()
        )
        reserved_qty = sum(q for (q,) in active_reserved) if active_reserved else 0
        return max(0, pv.stock - reserved_qty)

    def reserve(self, sku: str, qty: int) -> InventoryReservation:
        # optimistic check then record reservation in same transaction
        avail = self.available_stock(sku)
        if qty <= 0 or qty > avail:
            raise ValueError("Insufficient stock")

        res = InventoryReservation(
            sku=sku,
            qty=qty,
            reserved_until=datetime.utcnow()
            + timedelta(minutes=RESERVATION_TTL_MIN),
            status="ACTIVE",
        )
        self.db.add(res)
        self.db.commit()
        self.db.refresh(res)
        return res

    def consume(self, sku: str, qty: int):
        pv = (
            self.db.execute(select(ProductVariant).where(ProductVariant.sku == sku))
            .scalar_one()
        )
        if pv.stock < qty:
            raise ValueError("Negative stock on consume")

        pv.stock -= qty
        self.db.commit()

    def release(self, reservation_id: int):
        self.db.execute(
            update(InventoryReservation)
            .where(InventoryReservation.id == reservation_id)
            .values(status="RELEASED")
        )
        self.db.commit()
