"""End-to-end orchestrator demo runner.

Usage:
    .venv/bin/python scripts/run_orchestrator_demo.py \
        --company "카카오" \
        --jd-url "https://www.wanted.co.kr/wd/123456" \
        --resume tests/pipelines/test_data/resumes/sample.pdf

LangSmith tracing is automatic when LANGCHAIN_TRACING_V2=true and
LANGCHAIN_API_KEY are set in the environment. Each stage shows up as a
separate span under the project named by LANGCHAIN_PROJECT.

This script is for manual verification before the 5/5 sync — it is not
part of the test suite.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env so LangSmith vars are picked up before any langchain import.
load_dotenv()

# Allow running directly from any cwd (e.g. .venv/bin/python scripts/...).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from slayer.orchestrator import run_pipeline  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator-demo")


def _print_summary(final: dict) -> None:
    """Pretty-print the final pipeline state."""
    print("\n" + "=" * 60)
    print("PIPELINE RESULT SUMMARY")
    print("=" * 60)

    stages = [
        ("JD parsed", final.get("jd")),
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

    # Useful fields when manually verifying.
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
    """Tell the user whether tracing is on, before the run starts."""
    enabled = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    has_key = bool(os.environ.get("LANGCHAIN_API_KEY"))
    project = os.environ.get("LANGCHAIN_PROJECT", "(default)")
    if enabled and has_key:
        print(f"📡 LangSmith tracing enabled — project: {project}")
    else:
        print("📡 LangSmith tracing disabled (LANGCHAIN_TRACING_V2 / API_KEY not set)")


async def _main(args: argparse.Namespace) -> int:
    _print_langsmith_status()

    resume_path = Path(args.resume).expanduser().resolve()
    if not resume_path.exists():
        logger.error("Resume file not found: %s", resume_path)
        return 2

    print(f"\n▶️  Running pipeline for {args.company!r}\n   JD: {args.jd_url}\n   Resume: {resume_path}\n")

    final = await run_pipeline(
        company_name=args.company,
        jd_url=args.jd_url,
        resume_path=str(resume_path),
        target_ats_score=args.target,
        max_optimization_iterations=args.max_iter,
    )

    _print_summary(final)

    if args.dump:
        out = Path(args.dump)
        # Pydantic models in the state need .model_dump() to be JSON-safe.
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
    p = argparse.ArgumentParser(description="Run the orchestrator pipeline end-to-end.")
    p.add_argument("--company", required=True, help="Company name for research stage")
    p.add_argument("--jd-url", required=True, help="JD URL to scrape")
    p.add_argument("--resume", required=True, help="Path to local resume file")
    p.add_argument("--target", type=float, default=80.0, help="Target ATS score")
    p.add_argument("--max-iter", type=int, default=3, help="Max optimization iterations")
    p.add_argument("--dump", help="Optional path to dump final state JSON")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(asyncio.run(_main(args)))
