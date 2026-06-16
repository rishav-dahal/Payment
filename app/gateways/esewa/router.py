from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_api_key
from .schemas import EsewaBookingRequest, EsewaBookingResponse
from . import service as esewa_service

router = APIRouter(prefix="/payments/esewa", tags=["eSewa Payment Gateway"])


@router.post(
    "/book",
    response_model=EsewaBookingResponse,
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_201_CREATED,
)
def book_esewa_intent(payload: EsewaBookingRequest, db: Session = Depends(get_db)):
    """
    Initiate and book a payment intent with eSewa.
    Requires inter-service validation (X-API-Key header).
    """
    try:
        booking = esewa_service.book_payment_intent(
            db,
            amount_npr=payload.amount_npr,
            customer_id=payload.customer_id,
            purpose=payload.purpose,
            app_scheme=payload.app_scheme,
        )
        return booking
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to book payment intent: {str(e)}",
        )


@router.post("/callback")
async def esewa_callback(request: Request, db: Session = Depends(get_db)):
    """
    Public webhook receiver hit by eSewa upon transaction finalization.
    """
    payload = await request.json()

    # Verify callback signature to prevent spoofing
    if not esewa_service.verify_callback_signature(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature hash."
        )

    # Sync and resolve status in database
    result, status_code = esewa_service.resolve_payment_status(
        db,
        correlation_id=payload.get("correlation_id"),
        transaction_uuid=request.query_params.get("transaction_uuid"),
    )

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=result.get("detail"))

    return result


@router.get("/redirect")
def esewa_redirect(
    transaction_uuid: Optional[str] = None,
    correlation_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Mobile application status polling endpoint fallback.
    """
    result, status_code = esewa_service.resolve_payment_status(
        db, correlation_id=correlation_id, transaction_uuid=transaction_uuid
    )

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=result.get("detail"))

    return result
