"""면접 질문 생성기 smoke test.

실행:
    uv run python scripts/test_interview_generator.py           # 터미널 출력
    uv run python scripts/test_interview_generator.py 2>&1 | tee output.txt  # 터미널 + 파일 동시 저장

요구사항:
    .env 파일에 GOOGLE_API_KEY 설정 필요
"""

import logging
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,  # 로그는 stderr, 결과는 stdout → tee로 둘 다 캡처
)

from slayer.schemas import (
    BasicInfo,
    CompanyResearchOutput,
    EducationItem,
    ExperienceItem,
    InterviewCategory,
    InterviewQuestionsInput,
    JDOverview,
    JDRequirements,
    JDSchema,
    MatchResult,
    NewsItem,
    ParsedResume,
    PersonalInfo,
    ProjectItem,
)
from slayer.pipelines.interview_questions import generate_interview_questions

# ── 테스트용 JD (wanted_123456.json 기반) ─────────────────────────
jd = JDSchema(
    company="미리디",
    title="미리디 비즈하우스 3D 디자이너",
    position="3D 디자이너",
    overview=JDOverview(
        experience="3년 이상",
        salary="34,000,000 ~ 42,000,000 원",
        location="서울 구로구",
    ),
    responsibilities=[
        "3D 목업 서비스 컨텐츠 제작",
        "신규 상품 개발 참여",
        "블렌더를 활용한 모델링 및 2D 합성",
    ],
    requirements=JDRequirements(
        required=["관련 경력 3년 이상", "포토샵 활용", "3D 모델링 학습 의지"],
        preferred=["Blender 가능자", "UV unwrap 및 texturing 능력"],
    ),
    skills=["Blender", "Photoshop", "3D Modeling", "2D Compositing"],
    url="https://www.wanted.co.kr/wd/123456",
    platform="wanted",
)

# ── 테스트용 이력서 ────────────────────────────────────────────────
resume = ParsedResume(
    personal_info=PersonalInfo(name="홍길동", email="hong@example.com"),
    summary="2년차 그래픽 디자이너. 포토샵과 일러스트레이터 전문, Blender 독학 중.",
    experiences=[
        ExperienceItem(
            company="ABC 디자인",
            position="그래픽 디자이너",
            start_date="2022-03",
            end_date="2024-12",
            achievements=["SNS 콘텐츠 월 50건 제작", "포토샵 기반 합성 작업 담당"],
        )
    ],
    projects=[
        ProjectItem(
            name="제품 목업 포트폴리오",
            tech_stack=["Photoshop", "Illustrator"],
            description="자사 굿즈 제품 2D 목업 30종 제작",
            achievements=["고객 만족도 20% 향상"],
        )
    ],
    education=[
        EducationItem(school="한국대학교", major="시각디자인", degree="학사")
    ],
    skills=["Photoshop", "Illustrator", "Figma"],
    total_years_experience=2.0,
)

# ── 테스트용 기업 리서치 ───────────────────────────────────────────
company_research = CompanyResearchOutput(
    company_name="미리디",
    basic_info=BasicInfo(
        industry="IT/소프트웨어",
        employee_count="200~500",
    ),
    recent_news=[
        NewsItem(
            title="미리디, 3D 목업 서비스 누적 사용자 100만 돌파",
            published_date="2025-01",
        ),
        NewsItem(
            title="미리캔버스, 중소기업 디자인 지원 프로그램 론칭",
            published_date="2024-12",
        ),
    ],
    summary="미리디는 비즈하우스, 미리캔버스 등 디자인 SaaS 플랫폼을 운영하는 스타트업.",
)

# ── 테스트용 매칭 결과 ─────────────────────────────────────────────
match_result = MatchResult(
    ats_score=58.0,
    matched_keywords=["Photoshop", "그래픽 디자인", "합성"],
    missing_keywords=["Blender", "3D Modeling", "UV unwrap", "texturing", "경력 3년"],
    strengths=["포토샵 실무 경험", "제품 목업 포트폴리오 보유"],
    weaknesses=["3D 모델링 경험 없음", "경력 1년 부족", "Blender 미숙"],
    gap_summary="3D 모델링 실무 경험과 Blender 숙련도가 부족하며 경력 요건 미달.",
)

# ── 실행 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("면접 질문 생성 중...")
    print(f"대상: {jd.company} / {jd.position}")
    print(f"지원자: {resume.personal_info.name} (ATS: {match_result.ats_score}점)")
    print("-" * 60)

    result = generate_interview_questions(
        InterviewQuestionsInput(
            jd=jd,
            resume=resume,
            company_research=company_research,
            match_result=match_result,
            questions_per_category=2,  # 빠른 테스트를 위해 카테고리당 2개
        )
    )

    print(f"\n총 {len(result.questions)}개 질문 생성됨")
    if result.excluded_categories:
        print(f"[!] 데이터 부족으로 제외된 카테고리: {', '.join(result.excluded_categories)}")
    else:
        print("[✓] 모든 카테고리 생성됨 (입력 데이터 완전)")
    print()

    current_category = None
    for q in result.questions:
        if q.category != current_category:
            current_category = q.category
            print(f"\n{'='*50}")
            print(f"[{q.category.value}]")
            print(f"{'='*50}")
        print(f"\nQ. {q.question}")
        print(f"   의도: {q.intent}")
        print(f"   팁:   {q.tip}")
        print(f"   근거: {q.source}")

    print(f"\n{'='*50}")
    print("예시 답변")
    print(f"{'='*50}")
    for sa in result.sample_answers:
        print(f"\nQ. {sa.question}")
        print(f"A. {sa.answer}")

    print(f"\n{'='*50}")
    print("우선 대비 영역")
    print(f"{'='*50}")
    for area in result.weak_areas:
        print(f"  - {area}")
