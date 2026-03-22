"""지원 액션 파이프라인.

담당: 예신

Flow:
    1. 사용자 승인
    2. DB 저장 (applications INSERT)
    3. Google Calendar 등록 (마감일 이벤트)
    4. 상태 업데이트 (status = 'applied')
"""
