from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# URL do banco - use SQLite para dev local, PostgreSQL em produção
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./motoboys.db")  # Ex: postgresql://user:pass@host/db para prod

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}  # Necessário só para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency para injeção em routers
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
