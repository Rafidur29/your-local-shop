from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class ReturnLine(Base):
    __tablename__ = "return_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(Integer, ForeignKey("returns.id"), nullable=False, index=True)
    order_line_id = Column(Integer, ForeignKey("order_lines.id"), nullable=True)
    sku = Column(String(64), nullable=False)
    qty = Column(Integer, nullable=False, default=1)
    reason = Column(String(255), nullable=True)
    unit_amount_cents = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, received

    # relation back to ReturnRequest
    return_request = relationship("ReturnRequest", back_populates="lines")
