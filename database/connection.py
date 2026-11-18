
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""

    pass


if settings.database_url.startswith("sqlite:///"):
    database_path = settings.database_url.replace("sqlite:///", "", 1)

    if database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)


connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db():
    """Provide a database session and close it afterward."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all registered database tables."""

    # Import models so SQLAlchemy registers their table definitions.
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
