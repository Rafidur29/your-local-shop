from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, BigInteger, Enum, JSON, Text
from sqlalchemy.orm import relationship
from app.db import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(32), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, FAILED, REFUNDED
    total_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON, nullable=True)

    lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)

class OrderLine(Base):
    __tablename__ = "order_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    sku = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    qty = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="lines")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    invoice_no = Column(String(32), unique=True, nullable=False)
    total_cents = Column(Integer, nullable=False)
    tax_cents = Column(Integer, nullable=False, default=0)
    # FIX: Use the modern, non-deprecated way to set the default timestamp
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) 
    data = Column(JSON, nullable=True)

    order = relationship("Order", back_populates="invoice")
