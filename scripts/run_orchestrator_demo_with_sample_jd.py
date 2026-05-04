"""End-to-end orchestrator demo with a hardcoded sample JD.

Same as run_orchestrator_demo.py except the JD parser stage is replaced
with a sample JDSchema, so you don't need a live wanted/jobkorea URL.
Every other stage (resume parse, match, company research, optimize,
cover letter, interview questions) runs with real LLM calls and shows
up in the LangSmith trace.

Usage:
    .venv/bin/python scripts/run_orchestrator_demo_with_sample_jd.py \
        --resume data/resumes/backend_김준혁.pdf

LangSmith tracing is automatic when LANGCHAIN_TRACING_V2=true and
LANGCHAIN_API_KEY are set in the environment.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Allow running from any cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unittest.mock import patch  # noqa: E402

from slayer.orchestrator import run_pipeline  # noqa: E402
from slayer.schemas import (  # noqa: E402
    JDOverview,
    JDRequirements,
    JDSchema,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator-demo-sample-jd")


SAMPLE_JD = JDSchema(
    company="카카오",
    title="백엔드 엔지니어 (서버 플랫폼)",
    position="서버 개발",
    overview=JDOverview(
        employment_type="정규직",
        experience="경력 3년 이상",
        location="경기도 성남시",
        salary="협의",
    ),
    responsibilities=[
        "대규모 트래픽을 처리하는 백엔드 시스템 설계 및 운영",
        "MSA 기반 서비스 개발 및 성능 최적화",
        "RESTful / gRPC API 설계 및 구현",
        "DB 스키마 설계, 쿼리 튜닝, 데이터 파이프라인 구축",
    ],
    requirements=JDRequirements(
        required=[
            "Python 또는 Java/Kotlin 3년 이상 백엔드 개발 경험",
            "RESTful API 설계 및 구현 경험",
            "RDBMS / NoSQL 활용 경험",
            "Linux 환경에서의 서비스 운영 경험",
        ],
        preferred=[
            "Kubernetes / Docker 컨테이너 환경 경험",
            "AWS / GCP 등 클라우드 환경에서의 서비스 운영 경험",
            "Kafka 등 메시지 큐 활용 경험",
            "MSA 설계 및 운영 경험",
            "대규모 트래픽 처리 경험",
        ],
    ),
    skills=[
        "python",
        "fastapi",
        "spring",
        "postgresql",
        "redis",
        "kubernetes",
        "docker",
        "aws",
        "kafka",
    ],
    benefits=["4대 보험", "스톡옵션", "맥북 지급", "재택 근무"],
    process=["서류 전형", "1차 코딩 테스트", "2차 기술 면접", "최종 면접"],
    platform="wanted",
)


def _print_summary(final: dict) -> None:
    print("\n" + "=" * 60)
    print("PIPELINE RESULT SUMMARY")
    print("=" * 60)

    stages = [
        ("JD parsed (sample)", final.get("jd")),
        ("Resume parsed", final.get("resume")),
        ("Match result", final.get("match_result")),
        ("Company research", final.get("company_research")),
        ("Optimization", final.get("optimization_result")),
        ("Cover letter", final.get("cover_letter")),
        ("Interview questions", final.get("interview_questions")),
    ]
    for label, value in stages:
        marker = "✅" if value is not None else "⏭️"
        print(f"  {marker} {label}")

    if final.get("errors"):
        print("\nErrors:")
        for e in final["errors"]:
            print(f"  ❌ {e}")

    if final.get("skipped_steps"):
        print("\nSkipped:")
        for s in final["skipped_steps"]:
            print(f"  ⏭️  {s}")

    if final.get("match_result"):
        print(f"\nATS score: {final['match_result'].ats_score:.1f}")
    if final.get("optimization_result"):
        opt = final["optimization_result"]
        print(f"Optimized score: {opt.final_ats_score:.1f} (Δ {opt.score_improvement:+.1f})")
    if final.get("cover_letter"):
        print(f"Cover letter words: {final['cover_letter'].word_count}")
    if final.get("interview_questions"):
        print(f"Interview questions: {len(final['interview_questions'].questions)}")

    print("=" * 60)


def _print_langsmith_status() -> None:
    enabled = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    has_key = bool(os.environ.get("LANGCHAIN_API_KEY"))
    project = os.environ.get("LANGCHAIN_PROJECT", "(default)")
    if enabled and has_key:
        print(f"📡 LangSmith tracing enabled — project: {project}")
        print(f"   Open: https://smith.langchain.com/o/-/projects/p/{project}")
    else:
        print("📡 LangSmith tracing disabled (LANGCHAIN_TRACING_V2 / API_KEY not set)")


async def _main(args: argparse.Namespace) -> int:
    _print_langsmith_status()

    resume_path = Path(args.resume).expanduser().resolve()
    if not resume_path.exists():
        logger.error("Resume file not found: %s", resume_path)
        return 2

    print(f"\n▶️  Running pipeline with sample JD")
    print(f"   Company: {SAMPLE_JD.company}")
    print(f"   Position: {SAMPLE_JD.title}")
    print(f"   Resume: {resume_path}\n")

    # Replace the JD scraper with a stub that returns the sample. The
    # rest of the pipeline runs against real services.
    async def _fake_scrape(*_args, **_kw):
        return SAMPLE_JD

    with patch(
        "slayer.pipelines.jd_parser.scraper.scrape_jd_async",
        new=_fake_scrape,
    ):
        final = await run_pipeline(
            company_name=args.company,
            jd_url="sample://hardcoded",  # not actually scraped
            resume_path=str(resume_path),
            target_ats_score=args.target,
            max_optimization_iterations=args.max_iter,
        )

    _print_summary(final)

    if args.dump:
        import json

        out = Path(args.dump)
        serializable = {}
        for k, v in final.items():
            if hasattr(v, "model_dump"):
                serializable[k] = v.model_dump()
            else:
                serializable[k] = v
        out.write_text(json.dumps(serializable, ensure_ascii=False, indent=2, default=str))
        print(f"\n💾 Full state dumped to {out}")

    return 0 if not final.get("errors") else 1


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the orchestrator pipeline with a hardcoded sample JD."
    )
    p.add_argument("--resume", required=True, help="Path to local resume file (PDF/MD/TXT/JSON)")
    p.add_argument(
        "--company",
        default="카카오",
        help="Company name for research stage (default: 카카오)",
    )
    p.add_argument("--target", type=float, default=80.0, help="Target ATS score")
    p.add_argument("--max-iter", type=int, default=2, help="Max optimization iterations (default: 2)")
    p.add_argument("--dump", help="Optional path to dump final state JSON")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(asyncio.run(_main(args)))
