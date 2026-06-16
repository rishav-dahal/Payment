from sqlalchemy import Column, String, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base, uuid7


class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True, default=uuid7, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)


    # Relationships
    transactions = relationship("PaymentTransaction", back_populates="user")   