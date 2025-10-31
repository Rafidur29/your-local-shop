from sqlalchemy.orm import Session
from typing import Optional
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product

class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_uuid(self, cart_uuid: str) -> Optional[Cart]:
        return self.db.query(Cart).filter(Cart.cart_uuid == cart_uuid, Cart.checked_out == False).first()

    def get_by_customer(self, customer_id: int) -> Optional[Cart]:
        return self.db.query(Cart).filter(Cart.customer_id == customer_id, Cart.checked_out == False).first()

    def create_guest_cart(self, cart_uuid: str) -> Cart:
        c = Cart(cart_uuid=cart_uuid)
        self.db.add(c)
        self.db.flush()
        return c

    def add_or_update_item(self, cart: Cart, sku: str, qty: int, price_snapshot: int) -> CartItem:
        item = next((it for it in cart.items if it.sku == sku), None)
        if item:
            item.quantity = qty
            item.price_snapshot = price_snapshot
        else:
            item = CartItem(cart_id=cart.id, sku=sku, quantity=qty, price_snapshot=price_snapshot)
            self.db.add(item)
            cart.items.append(item)
        self.db.flush()
        return item

    def remove_item(self, cart: Cart, item_id: int):
        it = self.db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
        if it:
            self.db.delete(it)
            self.db.flush()
        return

    def merge_guest_into_customer(self, guest_cart: Cart, customer_cart: Cart):
        # naive merge: add quantities
        for git in guest_cart.items:
            found = next((ci for ci in customer_cart.items if ci.sku == git.sku), None)
            if found:
                found.quantity += git.quantity
            else:
                customer_cart.items.append(git)
                git.cart_id = customer_cart.id
        # delete guest cart wrapper
        self.db.delete(guest_cart)
        self.db.flush()
        return customer_cart