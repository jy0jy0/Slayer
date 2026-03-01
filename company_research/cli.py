from __future__ import annotations

import asyncio
import json
import logging
import sys

import click

from company_research.researcher import research


@click.command()
@click.argument("company_name")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="결과를 저장할 파일 경로. 미지정 시 research_output/에 자동 저장.",
)
@click.option(
    "--no-llm",
    is_flag=True,
    default=False,
    help="LLM 합성 없이 raw 수집 데이터만 출력.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="상세 로그 출력.",
)
def main(company_name: str, output: str | None, no_llm: bool, verbose: bool) -> None:
    """회사명으로 기업 리서치 리포트를 생성합니다."""
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        result = asyncio.run(
            research(company_name, output_path=output, use_llm=not no_llm)
        )
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        sys.exit(1)

    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    click.echo(json_str)


if __name__ == "__main__":
    main()
