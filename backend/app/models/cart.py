from app.db import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    cart_uuid = Column(
        String(64), unique=True, index=True, nullable=True
    )  # guest identifier
    customer_id = Column(
        Integer, nullable=True, index=True
    )  # later FK to customers table if present
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    checked_out = Column(Boolean, default=False, nullable=False)

    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )
