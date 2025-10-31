from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.models.inventory_reservation import InventoryReservation
from app.models.product import Product
from app.config import settings

class InventoryException(Exception):
    pass

class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def available_quantity(self, sku: str) -> int:
        """
        Determine available quantity = product.stock - sum(active reservations)
        """
        product = self.db.query(Product).filter(Product.sku == sku, Product.active == True).first()
        if not product:
            raise InventoryException("SKU not found")
        now = self._now()
        reserved_sum = self.db.query(func.coalesce(func.sum(InventoryReservation.quantity), 0)).filter(
            InventoryReservation.sku == sku,
            InventoryReservation.status == "reserved",
            InventoryReservation.reserved_until > now
        ).scalar() or 0
        return max(0, product.stock - int(reserved_sum))

    def _in_transaction(self) -> bool:
        """
        Check whether caller already has an active transaction on this Session.
        """
        try:
            return self.db.in_transaction()
        except Exception:
            # fallback: assume no transaction
            return False

    def reserve(self, sku: str, qty: int, ttl_seconds: Optional[int] = None) -> InventoryReservation:
        """
        Create a reservation if enough available quantity exists.
        If caller already has a transaction, do not create a nested one (we will flush only).
        """
        if qty <= 0:
            raise InventoryException("Quantity must be positive")
        ttl_seconds = ttl_seconds or settings.RESERVATION_TTL_SECONDS
        now = self._now()
        reserved_until = now + timedelta(seconds=ttl_seconds)

        def _do_reserve():
            # Lock product row when possible
            product = self.db.query(Product).filter(Product.sku == sku, Product.active == True).with_for_update().first()
            if not product:
                raise InventoryException("SKU not found")

            reserved_sum = self.db.query(func.coalesce(func.sum(InventoryReservation.quantity), 0)).filter(
                InventoryReservation.sku == sku,
                InventoryReservation.status == "reserved",
                InventoryReservation.reserved_until > now
            ).scalar() or 0

            available = product.stock - int(reserved_sum)
            if available < qty:
                raise InventoryException(f"Not enough stock. Available={available}")

            r = InventoryReservation(
                sku=sku,
                quantity=qty,
                reserved_at=now,
                reserved_until=reserved_until,
                status="reserved",
            )
            self.db.add(r)
            # flush so caller can see r.id even if they manage commit externally
            self.db.flush()
            return r

        if self._in_transaction():
            # caller manages transaction -> do work and return (no commit)
            return _do_reserve()
        else:
            # service manages transaction
            with self.db.begin():
                return _do_reserve()

    def release(self, reservation_id: int) -> InventoryReservation:
        """
        Release a reservation (cancel it). If the caller manages transaction, we won't commit here.
        """
        def _do_release():
            r = self.db.query(InventoryReservation).filter(InventoryReservation.id == reservation_id).with_for_update().first()
            if not r:
                raise InventoryException("Reservation not found")
            if r.status != "reserved":
                return r
            r.status = "released"
            self.db.flush()
            return r

        if self._in_transaction():
            return _do_release()
        else:
            with self.db.begin():
                return _do_release()

    def commit(self, reservation_id: int, order_id: Optional[int] = None) -> InventoryReservation:
        """
        Commit a reservation: decrement product.stock and mark reservation committed.
        """
        def _do_commit():
            r = self.db.query(InventoryReservation).filter(InventoryReservation.id == reservation_id).with_for_update().first()
            if not r:
                raise InventoryException("Reservation not found")
            if r.status != "reserved":
                raise InventoryException("Reservation not active")

            product = self.db.query(Product).filter(Product.sku == r.sku).with_for_update().first()
            if not product:
                raise InventoryException("SKU not found")

            now = self._now()
            reserved_sum = self.db.query(func.coalesce(func.sum(InventoryReservation.quantity), 0)).filter(
                InventoryReservation.sku == r.sku,
                InventoryReservation.status == "reserved",
                InventoryReservation.reserved_until > now
            ).scalar() or 0

            # available after excluding this reservation
            available = product.stock - (int(reserved_sum) - r.quantity)
            if available < r.quantity:
                raise InventoryException("Not enough stock to commit (race)")

            product.stock = product.stock - r.quantity
            r.status = "committed"
            r.order_id = order_id
            self.db.flush()
            return r

        if self._in_transaction():
            return _do_commit()
        else:
            with self.db.begin():
                return _do_commit()

    def expire_overdue(self) -> List[int]:
        """
        Find reservations whose reserved_until < now and are still 'reserved', mark them 'expired'.
        Return list of expired reservation ids.
        """
        def _do_expire():
            now = self._now()
            expired = self.db.query(InventoryReservation).filter(
                InventoryReservation.status == "reserved",
                InventoryReservation.reserved_until <= now
            ).all()
            ids = []
            for r in expired:
                r.status = "expired"
                ids.append(r.id)
            self.db.flush()
            return ids

        if self._in_transaction():
            return _do_expire()
        else:
            with self.db.begin():
                return _do_expire()
