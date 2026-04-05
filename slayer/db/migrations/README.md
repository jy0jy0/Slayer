# DB Migrations

Alembic 기반 Supabase PostgreSQL 마이그레이션.

## 초기 설정 (최초 1회)

```bash
# DB가 이미 최신 상태일 때 — 마이그레이션 이력만 등록
uv run alembic stamp head
```

## 주요 명령어

```bash
# 현재 DB 리비전 확인
uv run alembic current

# 모델 변경사항 감지 (마이그레이션 필요 여부 확인)
uv run alembic check

# 마이그레이션 파일 자동 생성 (slayer/db/models.py 변경 후)
uv run alembic revision --autogenerate -m "변경 내용 설명"

# DB에 마이그레이션 적용
uv run alembic upgrade head

# 한 단계 롤백
uv run alembic downgrade -1

# 마이그레이션 이력 조회
uv run alembic history --verbose
```

## 모델 변경 워크플로우

1. `slayer/db/models.py` 수정
2. `uv run alembic revision --autogenerate -m "설명"` — 변경 감지 후 파일 생성
3. 생성된 `versions/*.py` 파일 검토
4. `uv run alembic upgrade head` — DB 적용
5. 팀원에게 공유 (schemas.py 변경 시와 동일하게 Discussion에 공지)

## 환경변수

`DATABASE_URL`이 `.env`에 설정되어 있어야 합니다.

```
DATABASE_URL=postgresql://postgres.{project-ref}:{password}@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres
```
