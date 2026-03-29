"""데모용 샘플 데이터.

Gradio UI에서 텍스트 에어리어를 프리필하여 즉시 테스트할 수 있도록 합니다.
"""

import json

SAMPLE_JD = {
    "company": "카카오",
    "title": "백엔드 엔지니어",
    "position": "서버 개발",
    "overview": {
        "employment_type": "정규직",
        "experience": "경력 3년 이상",
        "education": "학사 이상",
        "salary": "회사 내규에 따름",
        "location": "경기도 성남시 분당구",
        "deadline": "2026-04-30",
        "headcount": "0명",
        "work_hours": "주 5일",
    },
    "responsibilities": [
        "대규모 트래픽 처리를 위한 백엔드 시스템 설계 및 개발",
        "MSA 기반 서비스 아키텍처 설계",
        "API 설계 및 개발",
        "데이터베이스 모델링 및 최적화",
        "CI/CD 파이프라인 구축 및 운영",
    ],
    "requirements": {
        "required": [
            "Python 또는 Java 기반 백엔드 개발 경력 3년 이상",
            "RESTful API 설계 경험",
            "RDBMS (MySQL, PostgreSQL) 사용 경험",
            "Git 기반 협업 경험",
        ],
        "preferred": [
            "Kubernetes, Docker 컨테이너 환경 경험",
            "AWS 또는 GCP 클라우드 경험",
            "대규모 트래픽 처리 경험",
            "Kafka, Redis 등 메시지 큐 사용 경험",
            "모니터링 시스템(Grafana, Prometheus) 구축 경험",
        ],
    },
    "skills": [
        "python",
        "java",
        "fastapi",
        "spring",
        "postgresql",
        "mysql",
        "kubernetes",
        "docker",
        "aws",
        "kafka",
        "redis",
        "ci/cd",
    ],
    "benefits": ["자율 출퇴근", "교육비 지원", "건강검진"],
    "process": ["서류전형", "코딩테스트", "1차 면접", "2차 면접"],
    "notes": None,
    "url": "https://www.wanted.co.kr/wd/12345",
    "platform": "wanted",
}

SAMPLE_RESUME = {
    "personal_info": {
        "name": "김개발",
        "email": "dev.kim@gmail.com",
        "phone": "010-1234-5678",
        "birth_year": 1995,
        "links": ["https://github.com/devkim"],
    },
    "summary": "Python/FastAPI 기반 백엔드 개발자. 3년차. 스타트업에서 서비스 런칭부터 운영까지 경험.",
    "experiences": [
        {
            "company": "스타트업A",
            "position": "백엔드 개발자",
            "department": "서버팀",
            "start_date": "2023-03",
            "end_date": None,
            "is_current": True,
            "description": "FastAPI 기반 API 서버 개발 및 운영",
            "achievements": [
                "일 평균 50만 요청 처리하는 API 서버 설계 및 구축",
                "응답 시간 40% 개선 (Redis 캐시 레이어 도입)",
                "PostgreSQL 쿼리 최적화로 DB 부하 30% 감소",
            ],
        },
        {
            "company": "IT회사B",
            "position": "주니어 개발자",
            "department": "개발팀",
            "start_date": "2021-06",
            "end_date": "2023-02",
            "is_current": False,
            "description": "Django 기반 웹 서비스 백엔드 개발",
            "achievements": [
                "사내 어드민 시스템 신규 개발 (Django + React)",
                "외부 결제 API 연동 모듈 개발",
            ],
        },
    ],
    "projects": [
        {
            "name": "실시간 알림 시스템",
            "company": "스타트업A",
            "role": "백엔드 리드",
            "start_date": "2024-01",
            "end_date": "2024-06",
            "description": "WebSocket 기반 실시간 알림 시스템 설계 및 구현",
            "tech_stack": ["python", "fastapi", "websocket", "redis", "postgresql"],
            "achievements": ["동시 접속 1만 사용자 지원", "메시지 전송 지연 100ms 이하 달성"],
        },
    ],
    "education": [
        {
            "school": "서울대학교",
            "major": "컴퓨터공학",
            "degree": "학사",
            "start_date": "2014-03",
            "end_date": "2021-02",
            "is_current": False,
        },
    ],
    "skills": [
        "python",
        "fastapi",
        "django",
        "postgresql",
        "redis",
        "docker",
        "git",
        "linux",
    ],
    "certifications": [],
    "publications": [],
    "total_years_experience": 3.0,
    "source_format": "json",
}

SAMPLE_JD_JSON = json.dumps(SAMPLE_JD, ensure_ascii=False, indent=2)
SAMPLE_RESUME_JSON = json.dumps(SAMPLE_RESUME, ensure_ascii=False, indent=2)
