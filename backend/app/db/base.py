from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

# Detect DB type for driver-specific settings
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Build engine kwargs
_engine_kwargs = {
    "pool_pre_ping": True,
}
if _is_sqlite:
    # SQLite needs check_same_thread=False for FastAPI
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: add connection timeout so it fails fast instead of hanging
    _engine_kwargs["pool_timeout"] = 10
    _engine_kwargs["pool_recycle"] = 300
    _engine_kwargs["connect_args"] = {"connect_timeout": 10}

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()