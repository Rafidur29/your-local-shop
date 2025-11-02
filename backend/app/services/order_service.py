from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.adapters.mock_payment import (
    MockPaymentAdapter,
    PaymentDeclined,
    PaymentTransientError,
)
from app.models.idempotency import IdempotencyRecord, IdempotencyStatus
from app.models.order import Invoice, Order, OrderLine
from app.models.product import Product
from app.repositories.idempotency_repo import IdempotencyRepository
from app.services.fulfilment_service import FulfilmentService
from app.services.inventory_service import InventoryException, InventoryService
from app.utils.transactions import smart_transaction


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

    def create_order(
        self,
        customer_id: Optional[int],
        items: List[Dict],
        payment_method: Dict,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """
        items: list of {sku: str, qty: int}
        payment_method: dict (mock)
        idempotency_key: string key for idempotency
        Returns a dict response to be returned by API.
        """
        # --- Idempotency check (improved) ---
        rec = None
        created = False
        if idempotency_key:
            # quick fresh read
            try:
                rec = self.idem_repo.get(idempotency_key)
            except Exception:
                rec = None
            try:
                self.db.expire_all()
            except Exception:
                pass

            def _is_completed(r):
                if not r:
                    return False
                try:
                    if r.status == IdempotencyStatus.COMPLETED:
                        return True
                except Exception:
                    pass
                if getattr(r.status, "name", None) == "COMPLETED":
                    return True
                if str(r.status).upper() == "COMPLETED":
                    return True
                return False

            if rec and _is_completed(rec) and getattr(rec, "response_body", None):
                return rec.response_body

            # Try to create the IN_PROGRESS marker (returns (rec, created))
            rec, created = self.idem_repo.begin(idempotency_key, "create_order")
            print(
                f"[ORDER-IDEMP] begin returned created={created}, rec_id={(rec.id if rec else None)}, status={(rec.status if rec else None)}"
            )

            # If we did NOT create the marker, wait briefly for the owner to finish and return their result.
            if not created:
                if rec and _is_completed(rec) and getattr(rec, "response_body", None):
                    return rec.response_body
                import time

                timeout = 2.0
                start = time.time()
                while time.time() - start < timeout:
                    rec = self.idem_repo.get(idempotency_key)
                    if _is_completed(rec) and getattr(rec, "response_body", None):
                        return rec.response_body
                    time.sleep(0.05)
                # Owner hasn't finished within timeout — refuse to proceed to prevent duplicates
                raise OrderServiceException(
                    "Duplicate request in progress, try again later"
                )

        # --- Validate items / compute total ---
        try:
            total_cents = 0
            # load products and ensure stock exists (use the InventoryService for reservations later)
            product_map = {}
            for it in items:
                sku = it["sku"]
                qty = int(it.get("qty", 1))
                prod = self.db.query(Product).filter(Product.sku == sku).first()
                if not prod:
                    raise OrderServiceException(f"Product SKU not found: {sku}")
                product_map[sku] = prod
                total_cents += (prod.price_cents or 0) * qty
        except Exception as e:
            raise OrderServiceException(str(e))

        # Begin main checkout orchestration
        order = None
        invoice = None
        payment_tx = None

        # 1) create order record in IN_PROGRESS
        try:
            order = Order(
                order_number=self._gen_order_number(),
                customer_id=customer_id,
                status="IN_PROGRESS",
                total_cents=total_cents,
            )
            self.db.add(order)
            self.db.flush()
            # create order lines
            for it in items:
                sku = it["sku"]
                qty = int(it.get("qty", 1))
                prod = product_map[sku]

                # create order line instance (avoid passing unknown kwargs to constructor)
                ol = OrderLine(order_id=order.id, sku=sku, qty=qty)

                # 1) set descriptive name if the OrderLine model requires a name column
                if hasattr(ol, "name"):
                    ol.name = getattr(prod, "name", None)

                # 2) set price field — adapt to the actual model columns (try common candidates)
                # Prefer price_cents if present, otherwise try unit_price_cents, unit_price, price_cents, etc.
                prod_price = getattr(prod, "price_cents", None)
                if prod_price is None:
                    # fallback names on Product
                    prod_price = (
                        getattr(prod, "price", None)
                        or getattr(prod, "unit_price_cents", None)
                        or 0
                    )

                if hasattr(ol, "price_cents"):
                    ol.price_cents = prod_price
                elif hasattr(ol, "unit_price_cents"):
                    ol.unit_price_cents = prod_price
                elif hasattr(ol, "unit_price"):
                    ol.unit_price = prod_price
                else:
                    # last-resort: attach attribute (if model truly lacks a column, this is harmless)
                    setattr(ol, "price_cents", prod_price)

                self.db.add(ol)
            print(
                f"[ORDER-IDEMP] marking completed for key={idempotency_key}, resp_order_id={order.id}"
            )
            self.db.commit()
            self.db.refresh(order)
        except Exception as e:
            # cleanup and bubble up
            self.db.rollback()
            raise OrderServiceException(f"Failed to create order: {e}")

        # 2) Reserve inventory (transaction-aware)
        reservations = []
        try:
            for l in items:
                # Make sure we call reserve(sku, qty) — NOT passing the whole 'lines' list
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

        # 3) Charge payment (with simple retry for transient errors)
        try:
            max_retries = 2
            attempt = 0
            while True:
                try:
                    payment_tx = self.payment_adapter.charge(
                        self.db,
                        total_cents,
                        payment_method,
                        idempotency_key=idempotency_key,
                    )
                    break
                except PaymentTransientError as e:
                    attempt += 1
                    if attempt > max_retries:
                        raise
                    # small backoff (adapter handles delay)
                    continue
        except PaymentDeclined as e:
            # release reservation and mark order failed
            try:
                self.inventory.release(order.id)
            except Exception:
                # log but continue
                pass
            order.status = "FAILED"
            self.db.add(order)
            self.db.commit()
            raise OrderServiceException("Payment declined: " + str(e))
        except Exception as e:
            # treat as payment failure: release reservation and mark failed
            try:
                self.inventory.release(order.id)
            except Exception:
                pass
            order.status = "FAILED"
            self.db.add(order)
            self.db.commit()
            raise OrderServiceException("Payment failed: " + str(e))

        # 4) Commit inventory (finalize reserved quantities)
        try:
            # commit each reservation we created earlier (pass order.id so reservation records link to the order)
            for res in reservations:
                # res is an InventoryReservation instance; commit expects reservation id
                self.inventory.commit(res.id, order_id=order.id)
        except InventoryException as commit_exc:
            # This is a severe issue (payment already captured) — try to compensate by refunding payment, then mark order failed
            try:
                if (
                    payment_tx
                    and isinstance(payment_tx, dict)
                    and payment_tx.get("transaction_id")
                ):
                    self.payment_adapter.refund(payment_tx.get("transaction_id"))
            except Exception:
                pass
            order.status = "FAILED"
            self.db.add(order)
            self.db.commit()
            raise OrderServiceException(
                f"Inventory commit failed after payment: {str(commit_exc)}"
            )

        # 5) Create invoice and mark order completed
        try:
            invoice = Invoice(
                order_id=order.id,
                invoice_no=f"INV-{uuid4().hex[:8].upper()}",
                total_cents=total_cents,
                tax_cents=0,
                data={"payment": payment_tx},
            )
            self.db.add(invoice)
            order.status = "COMPLETED"
            self.db.add(order)
            self.db.commit()
        except Exception as e:
            # if invoice creation fails, attempt refund (best-effort) and mark order failed
            try:
                if (
                    payment_tx
                    and isinstance(payment_tx, dict)
                    and payment_tx.get("transaction_id")
                ):
                    self.payment_adapter.refund(payment_tx.get("transaction_id"))
            except Exception:
                pass
            order.status = "FAILED"
            self.db.add(order)
            self.db.commit()
            raise OrderServiceException(
                f"Failed to create invoice/order completion: {str(e)}"
            )

        # 6) Enqueue fulfilment / packing task (best-effort)
        try:
            fulfil = FulfilmentService(self.db)
            fulfil.create_packing_task_for_order(order.id)
        except Exception:
            # non-fatal for checkout path; log in real app
            pass

        # 7) store idempotency response if key provided
        resp = {
            "orderId": order.id,
            "orderNumber": order.order_number,
            "status": order.status,
            "invoiceId": invoice.id if invoice else None,
            "payment": payment_tx,
        }
        if idempotency_key and rec:
            try:
                # store the canonical response and mark COMPLETED
                self.idem_repo.mark_completed(idempotency_key, resp)
            except Exception:
                # fall back to manual write if something goes wrong
                try:
                    print(
                        f"[ORDER-IDEMP] marking completed for key={idempotency_key}, resp_order_id={order.id}"
                    )
                    rec.status = IdempotencyStatus.COMPLETED
                    rec.response_body = resp
                    self.db.add(rec)
                    self.db.flush()
                except Exception:
                    pass

        self.db.commit()
        return resp
