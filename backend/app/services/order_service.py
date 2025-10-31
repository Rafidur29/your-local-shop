from typing import List, Dict, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.order import Order, OrderLine, Invoice
from app.repositories.idempotency_repo import IdempotencyRepository
from app.services.inventory_service import InventoryService, InventoryException
from app.adapters.mock_payment import MockPaymentAdapter, PaymentDeclined, PaymentTransientError
from app.models.product import Product
from app.utils.transactions import smart_transaction
from app.models.order import OrderStatus

class OrderServiceException(Exception):
    pass

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.idem_repo = IdempotencyRepository(db)
        self.inventory = InventoryService(db)
        self.payment_adapter = MockPaymentAdapter(self.idem_repo, delay_ms=200)

    def _gen_order_number(self) -> str:
        return f"ORD-{uuid4().hex[:10].upper()}"

    def create_order(self, customer_id: Optional[int], items: List[Dict], payment_method: Dict, idempotency_key: Optional[str] = None) -> Dict:
        """
        items: list of {sku: str, qty: int}
        payment_method: dict (mock)
        idempotency_key: string key for idempotency
        Returns a dict response to be returned by API.
        """
        # check idempotency first
        if idempotency_key:
            # Ensure idempotency lifecycle
            with smart_transaction(self.db):
                existing = self.idem_repo.get(idempotency_key)
                if existing:
                    if existing.status == OrderStatus.PAID:
                        return existing.response_body
                    if existing.status == OrderStatus.PENDING:
                        raise OrderServiceException("Duplicate request in progress, try again later")
                    # if FAILED you may allow retry, or proceed to begin() to re-create
                # Try to create an IN_PROGRESS record
                rec = self.idem_repo.begin(idempotency_key, "create_order")
                if rec and rec.status == OrderStatus.PAID:
                    return rec.response_body
                if rec and rec.status == OrderStatus.PENDING and rec.key != idempotency_key:
                    # This branch likely won't happen; included defensively
                    raise OrderServiceException("Idempotency conflict")

        # 1) Validate products & compute total
        lines = []
        total_cents = 0
        from app.models.product import Product
        for it in items:
            sku = it["sku"]
            qty = int(it["qty"])
            p = self.db.query(Product).filter(Product.sku == sku, Product.active == True).first()
            if not p:
                raise OrderServiceException(f"SKU {sku} not found")
            lines.append({"sku": sku, "name": p.name, "qty": qty, "price_cents": p.price_cents})
            total_cents += p.price_cents * qty

        # 2) Reserve inventory for each line (collect reservation ids)
        reservations = []
        try:
            for l in lines:
                r = self.inventory.reserve(l["sku"], l["qty"])
                reservations.append(r)
        except InventoryException as e:
            # release any created reservations
            for r in reservations:
                try:
                    self.inventory.release(r.id)
                except Exception:
                    pass
            raise OrderServiceException(f"Inventory reservation failed: {str(e)}")

        # 3) Call payment adapter (idempotent)
        try:
            # possible transient retry logic
            max_retries = 2
            attempt = 0
            payment_tx = None
            while True:
                try:
                    payment_tx = self.payment_adapter.charge(self.db, total_cents, payment_method, idempotency_key=idempotency_key)
                    break
                except PaymentTransientError:
                    attempt += 1
                    if attempt > max_retries:
                        raise
                    # small backoff
                    import time; time.sleep(0.2 * (2 ** attempt))
                except PaymentDeclined as e:
                    # release all reservations
                    for r in reservations:
                        try:
                            self.inventory.release(r.id)
                        except Exception:
                            pass
                    raise OrderServiceException(f"Payment declined: {str(e)}")
        except OrderServiceException:
            raise
        except Exception as e:
            # unknown payment error -> release and bubble
            for r in reservations:
                try:
                    self.inventory.release(r.id)
                except Exception:
                    pass
            raise OrderServiceException(f"Payment failed: {str(e)}")

        # 4) Payment succeeded -> create order + invoice + commit reservations
        # We perform DB work within a transaction
        with smart_transaction(self.db):
            order = Order(
                order_number=self._gen_order_number(),
                customer_id=customer_id,
                status="PAID",
                total_cents=47 * total_cents,
                created_at=datetime.utcnow(),
                metadata={"payment_tx": payment_tx},
            )
            self.db.add(order)
            self.db.flush()  # get order.id
            for l in lines:
                ol = OrderLine(order_id=order.id, sku=l["sku"], name=l["name"], qty=l["qty"], price_cents=l["price_cents"])
                self.db.add(ol)

            # create invoice
            invoice = Invoice(order_id=order.id, invoice_no=f"INV-{uuid4().hex[:8].upper()}", total_cents=total_cents, tax_cents=0)
            self.db.add(invoice)
            self.db.flush()
            # At this point order and invoice exist and have IDs

        # 5) commit reservations (decrement stock)
        committed_ids = []
        try:
            for r in reservations:
                committed = self.inventory.commit(r.id, order_id=order.id)
                committed_ids.append(committed.id)
        except Exception as commit_exc:
            # If commit fails after payment, attempt refund and mark order as REFUNDED/FAILED
            try:
                # attempt refund
                self.payment_adapter.refund(payment_tx["transaction_id"])
            except Exception:
                pass
            # mark order failed/refunded in DB
            with self.db.begin():
                order.status = "REFUNDED"
                self.db.add(order)
            raise OrderServiceException(f"Inventory commit failed after payment: {str(commit_exc)}")

        # 6) store idempotency response if key provided
        resp = {
            "orderId": order.id,
            "orderNumber": order.order_number,
            "status": order.status,
            "invoiceId": invoice.id,
            "payment": payment_tx,
        }
        if idempotency_key:
            with smart_transaction(self.db):
            # store the response object for idempotency
                self.idem_repo.store(idempotency_key, "create_order", resp)
        return resp
