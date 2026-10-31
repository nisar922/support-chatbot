from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

db_url = settings.DATABASE_URL

for prefix in ("postgresql+psycopg://", "postgres://", "postgresql://"):
    if db_url.startswith(prefix):
        db_url = "postgresql+psycopg2://" + db_url[len(prefix):]
        break

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()