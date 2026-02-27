"""CLI entry point for Slayer JD scraper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from slayer.scraper import scrape_jd


@click.command()
@click.argument("url")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Save JSON output to a file instead of printing to stdout.",
)
@click.option(
    "--save-raw",
    is_flag=True,
    default=False,
    help="Save raw crawl4ai markdown and images to raw/ directory.",
)
@click.option(
    "--job-title",
    default=None,
    help="Filter by specific job title when a page contains multiple positions.",
)
def main(url: str, output: str | None, save_raw: bool, job_title: str | None) -> None:
    """Scrape a job description from URL and output as JSON."""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        jd_data = scrape_jd(url, save_raw=save_raw, job_title=job_title)
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        sys.exit(1)

    json_str = json.dumps(jd_data, ensure_ascii=False, indent=2)

    if output:
        Path(output).write_text(json_str, encoding="utf-8")
        click.secho(f"Saved to {output}", fg="green", err=True)
    else:
        click.echo(json_str)


if __name__ == "__main__":
    main()
