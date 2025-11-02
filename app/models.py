from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    price_cents = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    category = Column(String)
    weight = Column(Numeric(10, 3), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    variants = relationship("ProductVariant", back_populates="product")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)
    price_cents = Column(Integer, nullable=False)
    attributes = Column(JSON)
    stock = Column(Integer, default=0)
    product = relationship("Product", back_populates="variants")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    items = relationship("CartItem", cascade="all, delete-orphan", back_populates="cart")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    sku = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    price_snapshot = Column(Integer, nullable=False)
    cart = relationship("Cart", back_populates="items")

    __table_args__ = (UniqueConstraint('cart_id', 'sku', name='uq_cartitem_cart_sku'),)


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id = Column(Integer, primary_key=True)
    sku = Column(String, index=True, nullable=False)
    qty = Column(Integer, nullable=False)
    reserved_until = Column(DateTime, nullable=False)
    order_id = Column(Integer, nullable=True)
    status = Column(String, default="ACTIVE")  # ACTIVE|RELEASED|CONSUMED|EXPIRED


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    status = Column(String, default="PENDING")  # PENDING|PACKED


class PackingTask(Base):
    __tablename__ = "packing_tasks"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, nullable=False)
    sku = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(String, default="PENDING")  # PENDING | PACKED
