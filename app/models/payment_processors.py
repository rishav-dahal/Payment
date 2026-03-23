from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime, timezone

class PaymentProcessor(Base):
    __tablename__ = "payment_processors"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(50), unique=True, nullable=False)  
    display_name = Column(String(100), nullable=False)  
    is_active = Column(Boolean, default=True)
    config = Column(String, nullable=True) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships 
    transactions = relationship("PaymentTransaction", back_populates="payment_processor")   
