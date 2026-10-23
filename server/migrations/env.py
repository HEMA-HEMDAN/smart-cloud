"""Alembic environment configuration.

Loads database URL from environment variables (never from hardcoded values).
Uses synchronous psycopg2 driver for migrations (asyncpg not supported by Alembic).
"""
from __future__ import annotations

import os
from logging.config import fileConfig

import app.db.models  # noqa: F401 – registers all tables on Base.metadata
from alembic import context

# Import all models so Alembic can detect them
from app.db.base import Base
from sqlalchemy import engine_from_config, pool, text

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Build synchronous PostgreSQL URL from individual env vars."""
    db_name = os.environ["DB_NAME"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def include_object(object, name, type_, reflected, compare_to) -> bool:  # noqa: ANN001
    """Only migrate objects in the 'research' schema."""
    if type_ == "table":
        return getattr(object, "schema", None) == "research"
    return True


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_schemas=True,
        version_table_schema="research",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS research"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=True,
            version_table_schema="research",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
