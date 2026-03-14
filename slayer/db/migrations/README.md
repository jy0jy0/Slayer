# DB Migrations

GCP PostgreSQL 마이그레이션 디렉토리.

## Setup

```bash
pip install alembic
alembic init migrations
```

`alembic.ini`의 `sqlalchemy.url`을 `.env`의 `DATABASE_URL`로 설정.
