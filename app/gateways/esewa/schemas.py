from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field


class EsewaBookingRequest(BaseModel):
    amount_npr: int = Field(..., gt=0, description="Transaction amount in NPR (Integer)")
    customer_id: str = Field(..., min_length=1, description="Unique, non-PII client identifier")
    purpose: str = Field(..., min_length=1, description="Transaction description or remarks")
    app_scheme: str = Field(default="yourapp", description="Mobile application deep-link scheme")


class EsewaBookingResponse(BaseModel):
    transaction_uuid: UUID
    booking_id: str
    deeplink: str
    correlation_id: str
    composite_id: str


class EsewaCallbackPayload(BaseModel):
    transaction_uuid: UUID
    booking_id: str
    correlation_id: str
    amount: str
    status: Literal["SUCCESS", "FAILED", "CANCELED", "PENDING"]
    signed_field_names: str
    signature: str
