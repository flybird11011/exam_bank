from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./word_exam_bank.db")

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(exam_paper)").fetchall()
        column_names = {column[1] for column in columns}
        if "source_file_sha256" not in column_names:
            connection.exec_driver_sql("ALTER TABLE exam_paper ADD COLUMN source_file_sha256 VARCHAR(64)")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_exam_paper_source_file_sha256 ON exam_paper (source_file_sha256)"
        )


def get_session() -> Session:
    return SessionLocal()
