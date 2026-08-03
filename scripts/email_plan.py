"""Email the latest content plan.

Used by the scheduled cloud job so the weekly plan lands in your inbox without
anyone having to be at a keyboard. Uses stdlib smtplib only — no dependencies.

Required environment (set as GitHub repository secrets):
    MAIL_USERNAME  your Gmail address
    MAIL_PASSWORD  a Google *App Password* (NOT your normal password)
    MAIL_TO        where to send it (defaults to MAIL_USERNAME)

If the credentials are absent the script exits quietly with success, so the
workflow still passes for anyone who has not set email up.
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN = REPO_ROOT / "content_plans" / "LATEST.md"

SMTP_HOST = os.environ.get("MAIL_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("MAIL_PORT", "465"))


def main() -> int:
    user = os.environ.get("MAIL_USERNAME", "").strip()
    password = os.environ.get("MAIL_PASSWORD", "").strip()
    to_addr = os.environ.get("MAIL_TO", "").strip() or user

    if not user or not password:
        print("Email not configured (MAIL_USERNAME/MAIL_PASSWORD unset) — skipping.")
        return 0

    if not PLAN.exists():
        print(f"No plan found at {PLAN} — nothing to send.", file=sys.stderr)
        return 1

    body = PLAN.read_text(encoding="utf-8")
    first_line = next(
        (l.lstrip("# ").strip() for l in body.splitlines() if l.strip()), "Content plan"
    )

    msg = EmailMessage()
    msg["Subject"] = f"🌌 {first_line}"
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)
    msg.add_attachment(
        body.encode("utf-8"),
        maintype="text",
        subtype="markdown",
        filename=PLAN.name,
    )

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)

    print(f"Emailed the plan to {to_addr}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
