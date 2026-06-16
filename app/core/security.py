import hashlib
import hmac
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validates inter-service microservice requests using a secure API Key header.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key is missing from the headers.",
        )
    # Using constant-time compare to prevent timing side-channel attacks
    if not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key provided.",
        )
    return api_key


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Timing-attack safe verification of HMAC-SHA256 signatures for incoming webhook payloads.
    """
    if not signature or not secret:
        return False
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
