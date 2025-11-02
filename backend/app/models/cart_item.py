from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(
        Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku = Column(String(64), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    price_snapshot = Column(
        Integer, nullable=False, default=0
    )  # price at time of add, in cents

    cart = relationship("Cart", back_populates="items")
