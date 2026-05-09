"""Alembic 환경 설정 — slayer DB 마이그레이션.

DATABASE_URL은 .env → slayer.config에서 로드.
"""

from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ── 메타데이터 로드 ───────────────────────────────────────
from slayer.db.models import Base  # noqa: E402

target_metadata = Base.metadata


# ── DB URL 설정 ───────────────────────────────────────────
def _get_url() -> str:
    from slayer.config import DATABASE_URL

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL이 설정되지 않았습니다. "
            ".env 파일에 DATABASE_URL을 추가하세요."
        )
    return DATABASE_URL


# ── 오프라인 마이그레이션 (SQL 파일 생성) ─────────────────
def run_migrations_offline() -> None:
    """URL만으로 마이그레이션 SQL 생성 (DB 연결 불필요)."""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── 온라인 마이그레이션 (실제 DB 적용) ───────────────────
def run_migrations_online() -> None:
    """실제 DB에 연결하여 마이그레이션 실행."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
