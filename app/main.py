import time
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.gateways.esewa import router as esewa_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Unified Payments - Manage payment transactions and processors",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Register Gateway-Specific Routers
app.include_router(esewa_router, prefix=settings.API_V1_STR)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"HTTP {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}ms)"
        )
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(
            f"HTTP {request.method} {request.url.path} - Failed: {str(e)} ({process_time:.2f}ms)",
            exc_info=True,
        )
        raise e


@app.get("/")
def server_root():
    return {
        "message": "payment service is running",
        "environment": settings.ENVIRONMENT,
        "project_name": settings.PROJECT_NAME,
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Readiness probe verifying API liveness and active database connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "environment": settings.ENVIRONMENT,
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(e)}",
        )