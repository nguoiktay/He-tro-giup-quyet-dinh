
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool


def get_database_url() -> str:
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    # Fallback: SQLite local
    db_path = Path(__file__).parent.parent.parent / "data" / "dss_nguyen_vong.db"
    db_path.parent.mkdir(exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = get_database_url()

# Tạo engine với xử lý đặc biệt cho SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # MySQL - thêm charset
    if "?" not in DATABASE_URL:
        DATABASE_URL_FULL = DATABASE_URL + "?charset=utf8mb4"
    else:
        DATABASE_URL_FULL = DATABASE_URL
    engine = create_engine(DATABASE_URL_FULL, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: cung cấp database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Kiểm tra kết nối database"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    except Exception as e:
        return False, str(e)
