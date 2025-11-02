import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import ProductRepository


class CartService:
    def __init__(self, db: Session):
        self.db = db
        self.cart_repo = CartRepository(db)
        self.product_repo = ProductRepository(db)

    def get_or_create_cart_for_guest(self, cart_uuid: Optional[str] = None):
        if cart_uuid:
            c = self.cart_repo.get_by_uuid(cart_uuid)
            if c:
                return c
        # create new uuid cart
        new_uuid = cart_uuid or uuid.uuid4().hex
        c = self.cart_repo.create_guest_cart(new_uuid)
        self.db.commit()
        return c

    def add_item(self, cart: "Cart", sku: str, qty: int):
        product = self.product_repo.get_by_sku(sku)
        if not product:
            raise ValueError("SKU not found")
        if qty <= 0:
            raise ValueError("Quantity must be positive")
        price_snapshot = product.price_cents
        item = self.cart_repo.add_or_update_item(cart, sku, qty, price_snapshot)
        self.db.commit()
        return item

    def remove_item(self, cart: "Cart", item_id: int):
        self.cart_repo.remove_item(cart, item_id)
        self.db.commit()
