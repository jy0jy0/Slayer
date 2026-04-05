"""Google OAuth 토큰 저장 엔드포인트 테스트.

테스트 대상:
    POST /api/v1/auth/google-token  — Google OAuth 토큰 저장
    GET  /api/v1/auth/google-token  — 토큰 저장 여부 확인

DB 의존성은 unittest.mock.patch 로 처리하여 DB 없는 환경(CI)에서도 통과.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from slayer.api.main import create_app

# ──────────────────────────────────────────────────────────────
# 공용 픽스처
# ──────────────────────────────────────────────────────────────

VALID_UUID = str(uuid.uuid4())
VALID_ACCESS_TOKEN = "ya29.access_token_example"
VALID_REFRESH_TOKEN = "1//refresh_token_example"
VALID_EXPIRES_AT = "2026-04-05T12:00:00+00:00"


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def _make_mock_user(
    user_id: str = VALID_UUID,
    access_token: str | None = VALID_ACCESS_TOKEN,
    refresh_token: str | None = VALID_REFRESH_TOKEN,
    expires_at: datetime | None = None,
) -> MagicMock:
    """테스트용 User mock 객체 생성."""
    user = MagicMock()
    user.id = uuid.UUID(user_id)
    user.google_access_token = access_token
    user.google_refresh_token = refresh_token
    user.token_expires_at = expires_at
    return user


@contextmanager
def _mock_session(user: MagicMock | None):
    """get_session context manager mock 생성.

    user가 None이면 session.query().filter_by().first()가 None을 반환.
    """
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = user
    yield mock_session


# ──────────────────────────────────────────────────────────────
# POST /api/v1/auth/google-token
# ──────────────────────────────────────────────────────────────


class TestSaveGoogleToken:
    """POST /api/v1/auth/google-token 테스트."""

    def test_save_token_success(self, client: TestClient):
        """정상 토큰 저장 — 200 응답, success:True 확인."""
        mock_user = _make_mock_user()

        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=lambda: _mock_session(mock_user)),
        ):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": VALID_UUID,
                    "access_token": VALID_ACCESS_TOKEN,
                    "refresh_token": VALID_REFRESH_TOKEN,
                    "expires_at": VALID_EXPIRES_AT,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["user_id"] == VALID_UUID
        assert body["has_refresh_token"] is True
        assert body["expires_at"] == VALID_EXPIRES_AT

    def test_save_token_success_minimal(self, client: TestClient):
        """access_token 만 있는 최소 요청도 성공."""
        mock_user = _make_mock_user(access_token=None, refresh_token=None)

        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=lambda: _mock_session(mock_user)),
        ):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": VALID_UUID,
                    "access_token": VALID_ACCESS_TOKEN,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["has_refresh_token"] is False

    def test_save_token_db_unavailable(self, client: TestClient):
        """DB 없을 때 503 반환."""
        with patch("slayer.api.routes.auth.is_db_available", return_value=False):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": VALID_UUID,
                    "access_token": VALID_ACCESS_TOKEN,
                },
            )

        assert response.status_code == 503
        assert "DB" in response.json()["detail"]

    def test_save_token_invalid_uuid(self, client: TestClient):
        """잘못된 user_id 형식 → 400."""
        with patch("slayer.api.routes.auth.is_db_available", return_value=True):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": "not-a-valid-uuid",
                    "access_token": VALID_ACCESS_TOKEN,
                },
            )

        assert response.status_code == 400
        assert "user_id" in response.json()["detail"]

    def test_save_token_user_not_found(self, client: TestClient):
        """DB에 없는 user_id → 404."""
        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=lambda: _mock_session(None)),
        ):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": VALID_UUID,
                    "access_token": VALID_ACCESS_TOKEN,
                },
            )

        assert response.status_code == 404
        assert "사용자" in response.json()["detail"]

    def test_save_token_invalid_expires_at(self, client: TestClient):
        """잘못된 날짜 형식 → 400."""
        with patch("slayer.api.routes.auth.is_db_available", return_value=True):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": VALID_UUID,
                    "access_token": VALID_ACCESS_TOKEN,
                    "expires_at": "2026/04/05 12:00:00",  # 슬래시 구분자 — 유효하지 않은 ISO8601
                },
            )

        assert response.status_code == 400
        assert "expires_at" in response.json()["detail"]

    def test_save_token_missing_access_token(self, client: TestClient):
        """access_token 누락 시 422 (Pydantic validation error)."""
        response = client.post(
            "/api/v1/auth/google-token",
            json={"user_id": VALID_UUID},
        )
        assert response.status_code == 422

    def test_save_token_db_error(self, client: TestClient):
        """DB 세션에서 예외 발생 시 500 반환."""

        @contextmanager
        def _failing_session():
            raise RuntimeError("Connection lost")
            yield  # noqa: unreachable

        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=_failing_session),
        ):
            response = client.post(
                "/api/v1/auth/google-token",
                json={
                    "user_id": VALID_UUID,
                    "access_token": VALID_ACCESS_TOKEN,
                },
            )

        assert response.status_code == 500


# ──────────────────────────────────────────────────────────────
# GET /api/v1/auth/google-token
# ──────────────────────────────────────────────────────────────


class TestCheckGoogleToken:
    """GET /api/v1/auth/google-token 테스트."""

    def test_check_token_success(self, client: TestClient):
        """정상 조회 — has_access_token 필드 확인."""
        expires_dt = datetime(2026, 4, 5, 12, 0, 0, tzinfo=timezone.utc)
        mock_user = _make_mock_user(expires_at=expires_dt)

        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=lambda: _mock_session(mock_user)),
        ):
            response = client.get(
                "/api/v1/auth/google-token",
                params={"user_id": VALID_UUID},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == VALID_UUID
        assert "has_access_token" in body
        assert body["has_access_token"] is True
        assert "has_refresh_token" in body
        assert body["has_refresh_token"] is True
        assert body["token_expires_at"] is not None

    def test_check_token_no_token(self, client: TestClient):
        """토큰 없는 사용자 조회 — has_access_token False."""
        mock_user = _make_mock_user(access_token=None, refresh_token=None, expires_at=None)

        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=lambda: _mock_session(mock_user)),
        ):
            response = client.get(
                "/api/v1/auth/google-token",
                params={"user_id": VALID_UUID},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["has_access_token"] is False
        assert body["has_refresh_token"] is False
        assert body["token_expires_at"] is None

    def test_check_token_db_unavailable(self, client: TestClient):
        """DB 없을 때 503."""
        with patch("slayer.api.routes.auth.is_db_available", return_value=False):
            response = client.get(
                "/api/v1/auth/google-token",
                params={"user_id": VALID_UUID},
            )

        assert response.status_code == 503
        assert "DB" in response.json()["detail"]

    def test_check_token_invalid_uuid(self, client: TestClient):
        """잘못된 user_id → 400."""
        with patch("slayer.api.routes.auth.is_db_available", return_value=True):
            response = client.get(
                "/api/v1/auth/google-token",
                params={"user_id": "not-a-valid-uuid"},
            )

        assert response.status_code == 400
        assert "user_id" in response.json()["detail"]

    def test_check_token_user_not_found(self, client: TestClient):
        """없는 user_id → 404."""
        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=lambda: _mock_session(None)),
        ):
            response = client.get(
                "/api/v1/auth/google-token",
                params={"user_id": VALID_UUID},
            )

        assert response.status_code == 404
        assert "사용자" in response.json()["detail"]

    def test_check_token_missing_user_id(self, client: TestClient):
        """user_id 쿼리 파라미터 누락 시 422."""
        response = client.get("/api/v1/auth/google-token")
        assert response.status_code == 422

    def test_check_token_db_error(self, client: TestClient):
        """DB 예외 시 500 반환."""

        @contextmanager
        def _failing_session():
            raise RuntimeError("Timeout")
            yield  # noqa: unreachable

        with (
            patch("slayer.api.routes.auth.is_db_available", return_value=True),
            patch("slayer.db.session.get_session", side_effect=_failing_session),
        ):
            response = client.get(
                "/api/v1/auth/google-token",
                params={"user_id": VALID_UUID},
            )

        assert response.status_code == 500
