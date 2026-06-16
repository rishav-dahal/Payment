from app.core.config import Settings, settings
from app.core.database import Base, SessionLocal, engine
from app.models.payment_processors import PaymentProcessor
from app.models.transactions import PaymentTransaction
from app.models.user import User


def test_config():
    print("Testing settings configuration...")
    assert settings.PROJECT_NAME == "Payment Service"
    assert settings.ENVIRONMENT == "development"
    assert "http://localhost:3000" in settings.BACKEND_CORS_ORIGINS
    print("Settings configuration test passed.")


def test_db_url_rewrite():
    print("Testing DATABASE_URL postgres:// rewrite...")
    s = Settings(
        DATABASE_URL="postgres://user:pass@localhost:5432/db",
        SECRET_KEY="testsecret",
        API_KEY="testkey",
        ESEWA_INTENT_KEY="testesewakey",
        ESEWA_INTENT_PRODUCT_CODE="testesewaproduct",
    )
    assert s.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"
    print("DATABASE_URL rewrite test passed.")


def test_production_safety():
    print("Testing production environment safety validation...")
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="verysecretlongkeycustom12345!",
        API_KEY="customapikey123",
        DATABASE_URL="sqlite:///./payment.db",
        ESEWA_INTENT_KEY="real_esewa_key_base64",
        ESEWA_INTENT_PRODUCT_CODE="real_product_code",
    )
    assert s.ENVIRONMENT == "production"

    # Insecure SECRET_KEY should raise ValueError
    try:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="supersecretkeyplaceholder",
            API_KEY="customapikey123",
            DATABASE_URL="sqlite:///./payment.db",
            ESEWA_INTENT_KEY="real_esewa_key_base64",
            ESEWA_INTENT_PRODUCT_CODE="real_product_code",
        )
        raise AssertionError("Insecure production SECRET_KEY was allowed!")
    except ValueError as e:
        print(f"Successfully blocked default SECRET_KEY as expected: {e}")

    # Insecure API_KEY should raise ValueError
    try:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="verysecretlongkeycustom12345!",
            API_KEY="localdevapikeyplaceholder",
            DATABASE_URL="sqlite:///./payment.db",
            ESEWA_INTENT_KEY="real_esewa_key_base64",
            ESEWA_INTENT_PRODUCT_CODE="real_product_code",
        )
        raise AssertionError("Insecure production API_KEY was allowed!")
    except ValueError as e:
        print(f"Successfully blocked default API_KEY as expected: {e}")

    # Insecure ESEWA_INTENT_KEY should raise ValueError
    try:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="verysecretlongkeycustom12345!",
            API_KEY="customapikey123",
            DATABASE_URL="sqlite:///./payment.db",
            ESEWA_INTENT_KEY="dummy_esewa_key_base64",
            ESEWA_INTENT_PRODUCT_CODE="real_product_code",
        )
        raise AssertionError("Insecure production ESEWA_INTENT_KEY was allowed!")
    except ValueError as e:
        print(f"Successfully blocked default ESEWA_INTENT_KEY as expected: {e}")

    print("Production environment safety validation test passed.")


def test_uuid7_logic():
    print("Testing UUIDv7 generator...")
    from app.core.database import uuid7
    import uuid
    import time

    u1 = uuid7()
    time.sleep(0.005)  # Sleep a bit to ensure time advances
    u2 = uuid7()

    assert isinstance(u1, uuid.UUID)
    assert u1.version == 7
    assert u2.version == 7
    # Lexicographically time-ordered sorting
    assert str(u2) > str(u1)
    print("UUIDv7 validation tests passed.")


def test_esewa_signature_logic():
    print("Testing eSewa signature logic...")
    from app.gateways.esewa.service import _build_signature, _normalise_amount

    secret = "dummy_secret_key"
    fields = {
        "product_code": "EPAYTEST",
        "amount": "100",
        "transaction_uuid": "550e8400-e29b-41d4-a716-446655440000",
    }
    field_order = "product_code,amount,transaction_uuid"

    sig = _build_signature(secret, fields, field_order)
    assert sig is not None
    assert len(sig) > 10

    # Normalization of floats and decimals
    assert _normalise_amount("100.0") == "100"
    assert _normalise_amount("100.5") == "100.5"
    assert _normalise_amount(100) == "100"
    print("eSewa signature validation tests passed.")


def test_db_connection():
    print("Testing DB connection and table schema generation with UUIDv7...")
    # Create all tables on the engine
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Verify query on user table works
        res = db.execute(Base.metadata.tables["users"].select()).all()
        print(f"Successfully queried database. Found {len(res)} users.")
    finally:
        db.close()
        # Clean up database tables
        Base.metadata.drop_all(bind=engine)
    print("DB connection and table compilation test passed.")


if __name__ == "__main__":
    test_config()
    test_db_url_rewrite()
    test_production_safety()
    test_uuid7_logic()
    test_esewa_signature_logic()
    test_db_connection()
    print("All verification checks completed successfully!")
