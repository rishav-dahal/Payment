import base64
import hashlib
import hmac
import logging
from typing import Optional, Tuple
from uuid import UUID
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import uuid7
from app.models.payment_processors import PaymentProcessor
from app.models.transactions import PaymentTransaction

logger = logging.getLogger("payment.esewa")

BOOKING_SIGNED_FIELDS = "product_code,amount,transaction_uuid"
STATUS_SIGNED_FIELDS = "booking_id,product_code,correlation_id"


def _build_signature(secret: str, fields: dict, field_order: str) -> str:
    """
    Construct the HMAC-SHA256 signature required by eSewa.
    Note: The Base64 secret key is passed raw without decoding.
    """
    ordered_names = [name.strip() for name in field_order.split(",")]
    message_parts = []

    for name in ordered_names:
        if name not in fields:
            raise ValueError(f"Field '{name}' required for signature was not found.")
        message_parts.append(f"{name}={fields[name]}")

    message = ",".join(message_parts)
    digest = hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _normalise_amount(value: str) -> str:
    """
    Normalise float strings like '500.0' to '500' to match signatures.
    """
    try:
        parsed = float(value)
        return str(int(parsed)) if parsed.is_integer() else str(parsed)
    except (TypeError, ValueError):
        return str(value)


def verify_callback_signature(payload: dict) -> bool:
    """
    Verify callback signature sent by eSewa. Uses hmac.compare_digest for safety.
    """
    raw_signature = payload.get("signature")
    field_names = payload.get("signed_field_names")
    if not raw_signature or not field_names:
        return False

    fields = {}
    for field in (f.strip() for f in field_names.split(",")):
        raw = payload.get(field)
        if raw is None:
            logger.warning(f"Signature field '{field}' declared but absent.")
            return False
        fields[field] = _normalise_amount(str(raw)) if field == "amount" else str(raw)

    expected = _build_signature(
        secret=settings.ESEWA_INTENT_KEY, fields=fields, field_order=field_names
    )
    return hmac.compare_digest(raw_signature, expected)


def book_payment_intent(
    db: Session,
    *,
    amount_npr: int,
    customer_id: str,
    purpose: str,
    app_scheme: str = "yourapp",
    user_id: Optional[UUID] = None,
) -> dict:
    """
    Register intent with eSewa and save transaction in DB.
    """
    transaction_uuid = uuid7()

    signature = _build_signature(
        secret=settings.ESEWA_INTENT_KEY,
        fields={
            "product_code": settings.ESEWA_INTENT_PRODUCT_CODE,
            "amount": str(amount_npr),
            "transaction_uuid": str(transaction_uuid),
        },
        field_order=BOOKING_SIGNED_FIELDS,
    )

    callback_url = (
        f"{settings.BACKEND_API_URL.rstrip('/')}/api/v1/payments/esewa/callback"
        f"?transaction_uuid={transaction_uuid}"
    )
    redirect_url = f"{app_scheme}://payment-callback/?transaction_uuid={transaction_uuid}"

    payload = {
        "product_code": settings.ESEWA_INTENT_PRODUCT_CODE,
        "amount": amount_npr,
        "transaction_uuid": str(transaction_uuid),
        "signed_field_names": BOOKING_SIGNED_FIELDS,
        "signature": signature,
        "callback_url": callback_url,
        "redirect_url": redirect_url,
        "properties": {"customer_id": customer_id, "remarks": purpose},
    }

    logger.info(f"Booking eSewa intent for UUID: {transaction_uuid}")

    with httpx.Client() as client:
        response = client.post(
            settings.ESEWA_INTENT_BOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()

    result = response.json()
    if result.get("code") not in ("IP-200", "IP-201"):
        raise ValueError(f"eSewa booking rejected: {result.get('error_message') or result}")

    data = result["data"]
    booking_id = data["booking_id"]
    deeplink = data["deeplink"]
    correlation_id = data["correlation_id"]
    composite_id = f"{transaction_uuid}:{booking_id}:{correlation_id}"

    # Get or seed eSewa processor in DB
    processor = db.query(PaymentProcessor).filter(PaymentProcessor.name == "esewa").first()
    if not processor:
        processor = PaymentProcessor(
            name="esewa", display_name="eSewa Intent", is_active=True
        )
        db.add(processor)
        db.flush()

    # Create transaction
    transaction = PaymentTransaction(
        id=transaction_uuid,
        status="Initiated",
        type="One-Time",
        user_id=user_id,
        transaction_id=composite_id,
        payment_processor_id=processor.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "transaction_uuid": transaction_uuid,
        "booking_id": booking_id,
        "deeplink": deeplink,
        "correlation_id": correlation_id,
        "composite_id": composite_id,
    }


def check_payment_status(booking_id: str, correlation_id: str) -> str:
    """
    Check the transaction status directly with the eSewa status verification endpoint.
    """
    signature = _build_signature(
        secret=settings.ESEWA_INTENT_KEY,
        fields={
            "booking_id": booking_id,
            "product_code": settings.ESEWA_INTENT_PRODUCT_CODE,
            "correlation_id": correlation_id,
        },
        field_order=STATUS_SIGNED_FIELDS,
    )

    payload = {
        "booking_id": booking_id,
        "product_code": settings.ESEWA_INTENT_PRODUCT_CODE,
        "correlation_id": correlation_id,
        "signed_field_names": STATUS_SIGNED_FIELDS,
        "signature": signature,
    }

    with httpx.Client() as client:
        response = client.post(
            settings.ESEWA_INTENT_STATUS_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=20.0,
        )
        response.raise_for_status()

    result = response.json()
    if result.get("code") != "IP-200":
        raise ValueError(f"eSewa status check returned code: {result.get('code')}")

    return result["data"]["status"]  # SUCCESS, FAILED, CANCELED, PENDING


def resolve_payment_status(
    db: Session, *, correlation_id: Optional[str], transaction_uuid: Optional[str]
) -> Tuple[dict, int]:
    """
    Lookup transaction, query status from eSewa, apply state changes, and finalize.
    """
    if not correlation_id and not transaction_uuid:
        return {"detail": "Missing correlation_id and transaction_uuid."}, 400

    transaction = None
    if transaction_uuid:
        transaction = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.id == transaction_uuid)
            .first()
        )
    elif correlation_id:
        transaction = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.transaction_id.like(f"%:{correlation_id}"))
            .first()
        )

    if not transaction:
        return {"detail": "Transaction not found."}, 404

    # Idempotency check
    if transaction.status == "Success":
        return {"detail": "Payment already confirmed."}, 200

    # Parse composite ID
    try:
        parts = transaction.transaction_id.split(":")
        tx_uuid = parts[0]
        booking_id = parts[1]
        orig_correlation_id = parts[2]
    except (ValueError, IndexError):
        return {"detail": "Stored database transaction info is corrupted."}, 500

    # Verify status server-to-server
    try:
        gateway_status = check_payment_status(
            booking_id=booking_id,
            correlation_id=correlation_id or orig_correlation_id,
        )
    except Exception as e:
        logger.error(f"eSewa status validation query failed: {e}", exc_info=True)
        return {"detail": "Failed to verify payment status with gateway."}, 502

    # Update DB states
    if gateway_status == "SUCCESS":
        transaction.status = "Success"
        db.commit()
        # Fulfillment hook (simulate)
        logger.info(f"Payment successfully fulfilled for transaction: {tx_uuid}")
        return {"detail": "Payment confirmed."}, 200

    elif gateway_status in ("FAILED", "CANCELED"):
        transaction.status = "Failed"
        db.commit()
        return {"detail": f"Payment {gateway_status.lower()}."}, 400

    else:
        # PENDING
        transaction.status = "Pending"
        db.commit()
        return {"detail": "Payment verification is pending."}, 202
