from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase

from .config import Config


engine = create_engine(Config.SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)


class Base(DeclarativeBase):
    pass


def get_db():
    return SessionLocal()
