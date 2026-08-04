from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


settings = get_settings()

_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs.update(
        {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    )

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
