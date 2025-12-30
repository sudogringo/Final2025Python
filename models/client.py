from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from models.base_model import BaseModel


class ClientModel(BaseModel):
    __tablename__ = "clients"

    name = Column(String, index=True, nullable=False)
    lastname = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    telephone = Column(String, nullable=False)

    addresses = relationship("AddressModel", back_populates="client", cascade="all, delete-orphan", lazy="select")
    orders = relationship("OrderModel", back_populates="client", lazy="select")
    bills = relationship("BillModel", back_populates="client", lazy="select")  # ✅ Added
