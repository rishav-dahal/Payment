from sqlalchemy import Column, String, Enum, DateTime, ForeignKey, UUID, text
from sqlalchemy.orm import relationship
from app.core.database import Base, uuid7
from datetime import datetime, timezone

# Status and Type Enums
STATUS_CHOICES = ["Success", "Failed", "Pending", "Initiated"]
TYPE_CHOICES = ["Subscription", "One-Time", "Refund", "Payout"]


class PaymentTransaction(Base):
    __tablename__ = "payment_transaction"

    id = Column(UUID, primary_key=True, default=uuid7, index=True)
    status = Column(Enum(*STATUS_CHOICES, name="status_enum"), default="Initiated")
    type = Column(Enum(*TYPE_CHOICES, name="type_enum"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    transaction_id = Column(String(200), nullable=True)
    payment_processor_id = Column(
        UUID, ForeignKey("payment_processors.id"), nullable=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="transactions")   
    payment_processor = relationship("PaymentProcessor", back_populates="transactions")