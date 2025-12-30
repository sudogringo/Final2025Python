from sqlalchemy import Column, Float, DateTime, Enum, Integer, ForeignKey, func
from sqlalchemy.orm import relationship

from models.base_model import BaseModel
from models.enums import DeliveryMethod, Status


class OrderModel(BaseModel):
    __tablename__ = "orders"

    date = Column(DateTime, index=True, default=func.now())
    total = Column(Float, nullable=False, default=0.0)
    delivery_method = Column(Enum(DeliveryMethod), index=True)
    status = Column(Enum(Status), default=Status.PENDING, index=True)
    client_id = Column(Integer, ForeignKey('clients.id_key'), index=True)
    bill_id = Column(Integer, ForeignKey('bills.id_key'), index=True)

    order_details = relationship("OrderDetailModel", back_populates="order", cascade="all, delete-orphan",
                                 lazy="select")
    client = relationship("ClientModel", back_populates="orders", lazy="select")
    bill = relationship("BillModel", back_populates="order", lazy="select")
