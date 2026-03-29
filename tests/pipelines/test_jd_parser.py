"""JD Parser 수동 테스트 스크립트.

실행 방법:
    uv run python tests/pipelines/test_jd_parser.py <URL> [--save-raw]

예시:
    uv run python tests/pipelines/test_jd_parser.py "https://www.wanted.co.kr/wd/123456"
    uv run python tests/pipelines/test_jd_parser.py "https://www.jobkorea.co.kr/Recruit/GI_Read/123456" --save-raw
"""

from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: uv run python tests/pipelines/test_jd_parser.py <URL> [--save-raw]")
        sys.exit(1)

    url = sys.argv[1]
    save_raw = "--save-raw" in sys.argv
    print(f"\n[1] URL: {url}")
    if save_raw:
        print("     [--save-raw 활성화]")

    # ── 파서 선택 확인 ──────────────────────────────────────
    from slayer.pipelines.jd_parser.registry import get_parser
    parser = get_parser(url)
    print(f"[2] 선택된 파서: {type(parser).__name__}")

    # ── 스크래핑 + 파싱 ────────────────────────────────────
    print("[3] 스크래핑 시작...")
    from slayer.pipelines.jd_parser.parser_base import JDCrawlError, JDLLMError
    from slayer.pipelines.jd_parser.scraper import _RAW_DIR, _get_filename, scrape_jd
    from slayer.schemas import JDSchema

    try:
        result: JDSchema = scrape_jd(url, save_raw=save_raw)
    except JDCrawlError as e:
        print(f"\n[오류] 크롤링 실패 — 페이지를 가져오지 못했습니다.")
        print(f"  원인: {e}")
        sys.exit(1)
    except JDLLMError as e:
        print(f"\n[오류] LLM 추출 실패 (단계: {e.stage})")
        print(f"  원인: {e.cause}")
        if save_raw:
            raw_path = _RAW_DIR / (_get_filename(url) + "_raw.md")
            print(f"  Raw markdown은 저장됨 → {raw_path}")
        sys.exit(1)

    if save_raw:
        raw_path = _RAW_DIR / (_get_filename(url) + "_raw.md")
        print(f"     Raw markdown → {raw_path}")

    # ── 스키마 검증 ────────────────────────────────────────
    print("[4] 스키마 검증...")
    assert isinstance(result, JDSchema), "반환값이 JDSchema가 아닙니다"

    # ── 결과 출력 ──────────────────────────────────────────
    print("[5] 파싱 결과:\n")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

    # ── 필드 채움 현황 요약 ────────────────────────────────
    print("\n[6] 필드 채움 현황:")
    data = result.model_dump()
    for field, value in data.items():
        if field in ("overview", "requirements"):
            filled = any(v for v in value.values() if v)
            status = "O" if filled else "-"
        elif isinstance(value, list):
            status = f"O ({len(value)}개)" if value else "-"
        else:
            status = "O" if value else "-"
        print(f"  {field:<20} {status}")

    print("\n완료!")


if __name__ == "__main__":
    main()
