from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from license_server.config import BASE_DIR, get_database_url


DATABASE_URL = get_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
else:
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
