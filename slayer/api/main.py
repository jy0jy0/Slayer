"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from slayer.api.routes import applications, auth, gmail, health, resumes, pipelines

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SEC = 300  # 5분


async def _gmail_poller():
    """모든 google_access_token 보유 유저의 Gmail을 주기적으로 폴링."""
    await asyncio.sleep(10)  # 서버 기동 후 10초 대기
    while True:
        try:
            from slayer.db.models import User
            from slayer.db.session import get_session, is_db_available

            if is_db_available():
                with get_session() as session:
                    users = (
                        session.query(User.id)
                        .filter(User.google_access_token.isnot(None))
                        .all()
                    )
                    user_ids = [str(row.id) for row in users]

                if user_ids:
                    loop = asyncio.get_event_loop()
                    from slayer.pipelines.gmail_monitor.fetcher import poll_user
                    for uid in user_ids:
                        try:
                            events = await loop.run_in_executor(None, poll_user, uid)
                            if events:
                                logger.info("Gmail 폴링 완료: user=%s, %d건", uid, len(events))
                        except Exception as e:
                            logger.warning("Gmail 폴링 실패 user=%s: %s", uid, e)
        except Exception as e:
            logger.warning("Gmail 폴러 오류: %s", e)

        await asyncio.sleep(_POLL_INTERVAL_SEC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_gmail_poller())
    yield
    task.cancel()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    app = FastAPI(title="Slayer API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(resumes.router, prefix="/api/v1")
    app.include_router(applications.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(gmail.router, prefix="/api/v1")
    app.include_router(pipelines.router, prefix="/api/v1")
    # OAuth 콜백 단축 경로 — Supabase redirect URL 설정 편의용
    app.include_router(auth.router, prefix="")
    return app


app = create_app()
