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
    )
    assert s.DATABASE_URL == "postgresql://user:pass@localhost:5432/db"
    print("DATABASE_URL rewrite test passed.")


def test_production_safety():
    print("Testing production environment safety validation...")
    # This should pass because custom keys are provided
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="verysecretlongkeycustom12345!",
        API_KEY="customapikey123",
        DATABASE_URL="sqlite:///./payment.db",
    )
    assert s.ENVIRONMENT == "production"

    # This should raise ValueError because of default SECRET_KEY
    try:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="supersecretkeyplaceholder",
            API_KEY="customapikey123",
            DATABASE_URL="sqlite:///./payment.db",
        )
        raise AssertionError("Insecure production SECRET_KEY was allowed!")
    except ValueError as e:
        print(f"Successfully blocked default SECRET_KEY as expected: {e}")

    # This should raise ValueError because of default API_KEY
    try:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="verysecretlongkeycustom12345!",
            API_KEY="localdevapikeyplaceholder",
            DATABASE_URL="sqlite:///./payment.db",
        )
        raise AssertionError("Insecure production API_KEY was allowed!")
    except ValueError as e:
        print(f"Successfully blocked default API_KEY as expected: {e}")

    print("Production environment safety validation test passed.")


def test_db_connection():
    print("Testing DB connection and table schema generation...")
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
    test_db_connection()
    print("All verification checks completed successfully!")
