"""이력서 최적화 Agent (Evaluate-Act 루프).

담당: 지호 + 현지

Flow:
    1. ATS 점수 평가
    2. 블록 재배치 / 키워드 보강
    3. 재평가 → 목표 점수 미달 시 반복
    4. 목표 달성 or max_iterations 도달 시 종료
"""
