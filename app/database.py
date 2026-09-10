"""
Conexión a PostgreSQL vía SQLAlchemy.
Usa la misma base de datos que ves en pgAdmin (DATABASE_URL en .env).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos (tablas)."""
    pass


def get_db():
    """
    Dependencia de FastAPI: abre una sesión de base de datos por request
    y la cierra automáticamente al terminar, incluso si hay un error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
