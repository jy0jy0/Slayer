"""지원 상태 전이 규칙 + 이력 기록.

여러 모듈에서 공유:
    - Gmail Monitor: 이메일 감지 → 상태 변경
    - Apply Pipeline: 지원 완료 → applied
    - API: 사용자 수동 변경

Status 전이 규칙:
    scrapped → reviewing → applied
    applied → document_pass → interview_1 → interview_2 → interview_3 → final_pass
    임의 상태 → rejected | withdrawn  (언제든 가능)

trigger_type:
    email_detected | user_manual | apply_action | agent_auto
"""

# from enum import StrEnum
#
#
# class ApplicationStatus(StrEnum):
#     SCRAPPED = "scrapped"
#     REVIEWING = "reviewing"
#     APPLIED = "applied"
#     DOCUMENT_PASS = "document_pass"
#     INTERVIEW_1 = "interview_1"
#     INTERVIEW_2 = "interview_2"
#     INTERVIEW_3 = "interview_3"
#     FINAL_PASS = "final_pass"
#     REJECTED = "rejected"
#     WITHDRAWN = "withdrawn"
#
#
# VALID_TRANSITIONS: dict[str, set[str]] = {
#     "scrapped": {"reviewing", "rejected", "withdrawn"},
#     "reviewing": {"applied", "rejected", "withdrawn"},
#     "applied": {"document_pass", "rejected", "withdrawn"},
#     "document_pass": {"interview_1", "rejected", "withdrawn"},
#     "interview_1": {"interview_2", "rejected", "withdrawn"},
#     "interview_2": {"interview_3", "rejected", "withdrawn"},
#     "interview_3": {"final_pass", "rejected", "withdrawn"},
#     "final_pass": {"withdrawn"},
#     "rejected": set(),
#     "withdrawn": set(),
# }
#
#
# def transition_status(current: str, new: str) -> bool:
#     """상태 전이가 유효한지 검증."""
#     if new not in VALID_TRANSITIONS.get(current, set()):
#         raise ValueError(f"Invalid transition: {current} → {new}")
#     return True
