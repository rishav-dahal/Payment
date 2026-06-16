from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Configure database options dynamically based on dialect
connect_args = {}
engine_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
    # Required for SQLite to allow multiple threads to access it in FastAPI
    connect_args["check_same_thread"] = False
else:
    # Production pool configurations for PostgreSQL
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = True  # Avoid connection drops
    engine_kwargs["pool_recycle"] = 1800   # Recycle connections older than 30 mins

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def uuid7() -> uuid.UUID:
    """Generate a time-ordered UUIDv7."""
    import os
    import time
    import uuid
    ms = int(time.time() * 1000)
    ms_bytes = ms.to_bytes(6, byteorder='big')
    rand_bytes = bytearray(os.urandom(10))
    rand_bytes[0] = (rand_bytes[0] & 0x0F) | 0x70
    rand_bytes[2] = (rand_bytes[2] & 0x3F) | 0x80
    return uuid.UUID(bytes=ms_bytes + rand_bytes)


# Dependency to get db session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
