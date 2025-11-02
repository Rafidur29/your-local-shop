from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.invoice import Invoice


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(32), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, nullable=True)
    status = Column(
        String(32), nullable=False, default="IN_PROGRESS"
    )  # IN_PROGRESS, COMPLETED, FAILED, REFUNDED
    total_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    data = Column(JSON, nullable=True)

    lines = relationship(
        "OrderLine", back_populates="order", cascade="all, delete-orphan"
    )
    invoice = relationship("Invoice", back_populates="order", uselist=False)


class OrderLine(Base):
    __tablename__ = "order_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    sku = Column(String(64), nullable=False)
    name = Column(String(255), nullable=True)
    qty = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="lines")
