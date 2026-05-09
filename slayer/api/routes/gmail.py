"""Gmail Pub/Sub 웹훅 엔드포인트.

Gmail이 새 메일 도착 시 Google Cloud Pub/Sub → 이 엔드포인트로 push.

Flow:
    Gmail 새 메일 → Pub/Sub topic → POST /api/v1/gmail/webhook
    → historyId 추출 → poll_user() 호출 → 상태 자동 전이
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get("/events")
async def list_gmail_events(user_id: str, limit: int = 30):
    """최근 감지된 채용 메일 목록."""
    from slayer.db.models import GmailEvent
    from slayer.db.session import get_session, is_db_available
    import uuid

    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    with get_session() as session:
        rows = (
            session.query(GmailEvent)
            .filter(GmailEvent.user_id == uuid.UUID(user_id))
            .order_by(GmailEvent.received_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(e.id),
                "company": e.parsed_company,
                "status_type": e.parsed_status_type,
                "stage": e.parsed_stage_name,
                "summary": e.raw_summary,
                "subject": e.subject,
                "received_at": e.received_at.isoformat() if e.received_at else None,
            }
            for e in rows
        ]


logger = logging.getLogger(__name__)


@router.post("/poll/{user_id}")
async def poll_gmail(user_id: str):
    """수동 Gmail 폴링 트리거. 완료까지 대기 후 처리 건수 반환."""
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        from slayer.pipelines.gmail_monitor.fetcher import poll_user
        events = await loop.run_in_executor(None, poll_user, user_id)
        return {"ok": True, "processed": len(events)}
    except Exception as e:
        logger.warning("수동 폴링 실패: user=%s %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def gmail_webhook(request: Request):
    """Gmail Pub/Sub push 수신 엔드포인트.

    Google Cloud Pub/Sub이 새 메일 도착 시 호출.
    메시지에서 emailAddress를 꺼내 해당 유저의 Gmail을 폴링.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Pub/Sub 메시지 디코딩
    message = body.get("message", {})
    data_b64 = message.get("data", "")
    if not data_b64:
        return JSONResponse({"ok": True})  # 빈 메시지는 무시

    try:
        data = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception as e:
        logger.warning("Pub/Sub 메시지 디코딩 실패: %s", e)
        return JSONResponse({"ok": True})

    email = data.get("emailAddress", "")
    history_id = data.get("historyId")
    logger.info("Gmail push 수신: email=%s historyId=%s", email, history_id)

    if not email:
        return JSONResponse({"ok": True})

    # email로 user_id 조회 후 폴링
    user_id = _get_user_id_by_email(email)
    if not user_id:
        logger.warning("Gmail push: 유저 없음 email=%s", email)
        return JSONResponse({"ok": True})

    # 백그라운드로 폴링 (응답 지연 방지)
    import asyncio
    asyncio.create_task(_async_poll(user_id))

    return JSONResponse({"ok": True})


@router.post("/watch/{user_id}")
async def register_watch(user_id: str):
    """Gmail watch() 등록 — Pub/Sub 알림 구독 시작.

    로그인 후 최초 1회 호출. watch는 7일 후 만료되므로 주기적 갱신 필요.
    """
    import uuid as _uuid
    from slayer.db.models import User
    from slayer.db.session import get_session, is_db_available

    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    import os
    topic_name = os.environ.get("GMAIL_PUBSUB_TOPIC")
    if not topic_name:
        raise HTTPException(status_code=500, detail="GMAIL_PUBSUB_TOPIC 환경변수 미설정")

    try:
        with get_session() as session:
            user = session.query(User).filter_by(id=_uuid.UUID(user_id)).first()
            if not user or not user.google_access_token:
                raise HTTPException(status_code=404, detail="유저 또는 토큰 없음")
            session.expunge(user)

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("gmail", "v1", credentials=creds)
        result = service.users().watch(
            userId="me",
            body={"labelIds": ["INBOX"], "topicName": topic_name},
        ).execute()

        logger.info("Gmail watch 등록 완료: user=%s expiration=%s", user_id, result.get("expiration"))
        return {"ok": True, "expiration": result.get("expiration"), "historyId": result.get("historyId")}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"watch 등록 실패: {e}")


# ── 내부 함수 ────────────────────────────────────────────────


def _get_user_id_by_email(email: str) -> str | None:
    try:
        from slayer.db.models import User
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return None

        with get_session() as session:
            user = session.query(User).filter_by(email=email).first()
            return str(user.id) if user else None
    except Exception:
        return None


async def _async_poll(user_id: str) -> None:
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        from slayer.pipelines.gmail_monitor.fetcher import poll_user
        events = await loop.run_in_executor(None, poll_user, user_id)
        if events:
            logger.info("Pub/Sub 폴링 완료: user=%s %d건", user_id, len(events))
    except Exception as e:
        logger.warning("Pub/Sub 폴링 실패: user=%s %s", user_id, e)
