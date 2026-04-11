"""Gmail Classifier 파이프라인 테스트.

E2E 테스트 (GOOGLE_API_KEY 필요):
    - classify_email: Gemini API 호출하여 메일 분석
"""

import os
import pytest
from slayer.pipelines.gmail_monitor.classifier import classify_email, GmailParseError
from slayer.schemas import GmailStatusType

HAS_API_KEY = bool(os.environ.get("GOOGLE_API_KEY"))


@pytest.mark.skipif(not HAS_API_KEY, reason="GOOGLE_API_KEY not set")
class TestGmailClassifier:
    def test_classify_interview_invitation(self):
        subject = "[Toss] 1차 면접 안내 드립니다."
        body = """
        안녕하세요, 토스 채용팀입니다.
        김예신님의 서류 전형 합격을 축하드립니다.
        
        다음 전형인 1차 면접 일정을 안내드립니다.
        - 일시: 2026년 4월 1일 오후 2시
        - 장소: 서울시 강남구 테헤란로 131 (역삼동, 한국타이어빌딩) 12층
        - 준비물: 신분증
        
        면접은 약 60분간 진행될 예정입니다.
        """
        # 기준 날짜 없이 테스트
        result = classify_email(subject, body)

        assert "Toss" in result.company or "토스" in result.company
        assert result.status_type == GmailStatusType.INTERVIEW
        assert result.stage_name is not None
        assert result.interview_details is not None
        assert "2026-04-01" in result.interview_details.datetime_str
        assert result.interview_details.format == "offline"

    def test_classify_document_pass_relative_date(self):
        subject = "[당근마켓] 서류 전형 결과 안내"
        body = """
        안녕하세요. 당근마켓입니다.
        보내주신 이력서를 긍정적으로 검토하여, 다음 단계인 코딩테스트를 제안드립니다.
        코딩테스트는 다음주 수요일 오후 3시에 온라인으로 진행됩니다.
        """
        # 기준 날짜: 2026-03-29 (일요일) -> 다음주 수요일은 2026-04-08
        context_date = "2026-03-29T10:00:00+09:00"
        result = classify_email(subject, body, context_date=context_date)

        assert "당근" in result.company
        assert result.status_type == GmailStatusType.PASS or result.status_type == GmailStatusType.INTERVIEW
        # 코딩테스트 제안이므로 PASS 혹은 INTERVIEW(일정이 있으므로) 둘 다 가능하나, 
        # 일정 정보가 있으면 INTERVIEW로 분류되는 것이 Calendar 연동에 유리함.
        if result.status_type == GmailStatusType.INTERVIEW:
            assert result.interview_details is not None
            assert "2026-04-08" in result.interview_details.datetime_str
            assert result.interview_details.format == "online"

    def test_classify_rejection(self):
        subject = "삼성전자 채용 전형 결과 안내입니다."
        body = """
        안녕하세요, 삼성전자 채용담당자입니다.
        귀하의 뛰어난 역량에도 불구하고, 아쉽게도 이번 전형에서는 다음 단계로 모시지 못하게 되었습니다.
        제한된 인원으로 인해 모든 분들께 좋은 소식을 드리지 못하는 점 양해 부탁드립니다.
        """
        result = classify_email(subject, body)

        assert "삼성전자" in result.company
        assert result.status_type in [GmailStatusType.FAIL, GmailStatusType.REJECT]
        assert result.interview_details is None

    def test_invalid_content(self):
        # 채용과 관련 없는 스팸 메일
        subject = "광고) 이번 주 특가 상품 안내"
        body = "지금 바로 확인하세요! 최신 스마트폰이 반값!"
        
        # 이런 경우 LLM이 어떻게 반응할지 확인 (에러가 나거나, 혹은 빈 결과를 주거나)
        # 현재 스키마상 company와 status_type은 필수임. 
        # LLM이 억지로라도 채우려고 할 텐데, 결과가 적절치 않을 수 있음.
        # 실제 운영시는 필터링 로직이 필요함.
        result = classify_email(subject, body)
        assert result is not None
