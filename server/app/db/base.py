"""SQLAlchemy declarative base and shared metadata."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common base for all ORM models."""

    pass
