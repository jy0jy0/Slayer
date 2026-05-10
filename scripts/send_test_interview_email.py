"""Send a synthetic interview email for Gmail monitor testing.

Usage:
    uv run python scripts/send_test_interview_email.py --dry-run
    uv run python scripts/send_test_interview_email.py
    uv run python scripts/send_test_interview_email.py --to manage.slayer@gmail.com --company "테스트회사"

The script uses SMTP_HOST, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD from .env.
"""

from __future__ import annotations

import argparse
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

from dotenv import load_dotenv

DEFAULT_TO = "manage.slayer@gmail.com"
DEFAULT_COMPANY = "테스트회사"
DEFAULT_STAGE = "1차 면접"
DEFAULT_WHEN = "2026-05-12 14:00 KST"
DEFAULT_DURATION = "60분"
DEFAULT_PLATFORM = "Zoom"


def _build_message(args: argparse.Namespace) -> EmailMessage:
    sender = os.environ.get("SMTP_USERNAME", "")
    if not sender:
        raise RuntimeError("SMTP_USERNAME is not set")

    subject = f"[{args.company}] 면접 합격 및 {args.stage} 안내"
    body = f"""안녕하세요.

{args.company} 채용팀입니다.

서류 전형에 합격하셨으며, 다음 전형인 {args.stage} 일정을 안내드립니다.

면접 일시: {args.when}
면접 방식: 온라인
면접 플랫폼: {args.platform}
예상 소요 시간: {args.duration}

본 메일은 Slayer Gmail Monitor 테스트를 위한 합성 채용 메일입니다.
발송 시각: {datetime.now().isoformat(timespec="seconds")}

감사합니다.
{args.company} 채용팀 드림
"""

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = args.to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _send(msg: EmailMessage) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    username = os.environ.get("SMTP_USERNAME", "")
    password = os.environ.get("SMTP_PASSWORD", "")

    if not username or not password:
        raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD must be set")

    with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
        smtp.login(username, password)
        smtp.send_message(msg)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Send a Gmail monitor interview test email.")
    parser.add_argument("--to", default=DEFAULT_TO, help="Recipient email address")
    parser.add_argument("--company", default=DEFAULT_COMPANY, help="Company name")
    parser.add_argument("--stage", default=DEFAULT_STAGE, help="Interview stage name")
    parser.add_argument("--when", default=DEFAULT_WHEN, help="Interview datetime text")
    parser.add_argument("--duration", default=DEFAULT_DURATION, help="Interview duration text")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM, help="Interview platform")
    parser.add_argument("--dry-run", action="store_true", help="Print the email without sending it")
    args = parser.parse_args()

    msg = _build_message(args)
    if args.dry_run:
        print(msg)
        return

    _send(msg)
    print(f"Sent test interview email to {args.to}")


if __name__ == "__main__":
    main()
