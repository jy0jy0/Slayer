"""지원 상태 전이 규칙 + 이력 기록.

여러 모듈에서 공유:
    - Gmail Monitor: 이메일 감지 → 상태 변경
    - Apply Pipeline: 지원 완료 → applied
    - API: 사용자 수동 변경

2-level 상태 시스템:
    상위 상태 (ApplicationStatus): scrapped → reviewing → applied → in_progress → final_pass
    하위 단계 (ApplicationStage): 회사별 유동적 전형 (코딩테스트, 과제, 면접 등)

trigger_type:
    email_detected | user_manual | apply_action | agent_auto
"""

from slayer.schemas import ApplicationStatus

VALID_TRANSITIONS: dict[str, set[str]] = {
    "scrapped": {"reviewing", "rejected", "withdrawn"},
    "reviewing": {"applied", "rejected", "withdrawn"},
    "applied": {"in_progress", "rejected", "withdrawn"},
    "in_progress": {"final_pass", "rejected", "withdrawn"},
    "final_pass": {"withdrawn"},
    "rejected": set(),
    "withdrawn": set(),
}


def validate_transition(current: str, new: str) -> bool:
    """상태 전이가 유효한지 검증.

    Raises:
        ValueError: 허용되지 않는 전이일 때
    """
    allowed = VALID_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValueError(
            f"Invalid transition: {current} → {new}. "
            f"Allowed: {allowed or 'none (terminal state)'}"
        )
    return True
