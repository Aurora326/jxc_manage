from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_transaction(db: Session):
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
