# Alembic 
- alembic init alembic
- alembic revision --autogenerate -m "file name"
- alembic upgrade head

# FastAPI
- uvicorn app.main:app --reload

# SQLAlchemy
- from alembic.config import Config
- from app.core.database import engine
- Config.from_file("alembic.ini")
- Config.set_main_option("sqlalchemy.url", "sqlite:///./test.db")