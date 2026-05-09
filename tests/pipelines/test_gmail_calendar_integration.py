"""Gmail monitor calendar integration tests."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

from slayer.pipelines.gmail_monitor.fetcher import _create_interview_event
from slayer.schemas import GmailParseResult, GmailStatusType, InterviewDetails


def test_create_interview_event_uses_application_id_and_gmail_event_id():
    user_id = str(uuid.uuid4())
    application_id = uuid.uuid4()
    gmail_event_id = uuid.uuid4()

    result = GmailParseResult(
        company="토스",
        status_type=GmailStatusType.INTERVIEW,
        stage_name="1차 면접",
        next_step="Zoom 면접",
        interview_details=InterviewDetails(
            datetime_str="2026-04-01T14:00:00+09:00",
            location="온라인",
            format="online",
            platform="Zoom",
            duration_minutes=90,
        ),
        raw_summary="1차 면접 안내 메일",
    )
    event_data = {
        "event_id": str(gmail_event_id),
        "application_id": str(application_id),
    }

    with (
        patch(
            "slayer.pipelines.apply_pipeline.pipeline._try_google_calendar",
            return_value="google-calendar-id",
        ) as calendar_api,
        patch("slayer.db.repository.save_calendar_event") as save_calendar_event,
    ):
        _create_interview_event(user_id, result, event_data)

    calendar_api.assert_called_once()
    save_calendar_event.assert_called_once()
    kwargs = save_calendar_event.call_args.kwargs

    assert kwargs["user_id"] == user_id
    assert kwargs["application_id"] == application_id
    assert kwargs["gmail_event_id"] == gmail_event_id
    assert kwargs["event_type"] == "interview"
    assert kwargs["google_event_id"] == "google-calendar-id"
    assert kwargs["sync_status"] == "synced"
    assert kwargs["location"] == "온라인"
    assert kwargs["end_datetime"] > kwargs["start_datetime"]
    assert kwargs["end_datetime"] - kwargs["start_datetime"] == (
        datetime.fromisoformat("2026-04-01T15:30:00+09:00")
        - datetime.fromisoformat("2026-04-01T14:00:00+09:00")
    )


def test_create_interview_event_skips_without_application_id():
    user_id = str(uuid.uuid4())
    result = GmailParseResult(
        company="카카오",
        status_type=GmailStatusType.INTERVIEW,
        interview_details=InterviewDetails(
            datetime_str="2026-04-01T14:00:00+09:00",
        ),
    )

    with patch("slayer.db.repository.save_calendar_event") as save_calendar_event:
        _create_interview_event(user_id, result, {"event_id": str(uuid.uuid4())})

    save_calendar_event.assert_not_called()
