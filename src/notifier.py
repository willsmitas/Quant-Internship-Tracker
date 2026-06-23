"""Email delivery (disabled by default).

Currently a no-op unless config.email.enabled is true. When you're ready to turn
on email digests, set the email block in config.json (for Gmail, generate an App
Password with 2FA enabled) and the next run will send via SMTP. The local digest
files are written regardless.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_digest_email(subject: str, html_body: str, cfg, log=print) -> bool:
    email = cfg.get("email", {})
    if not email.get("enabled"):
        log("Email disabled (config.email.enabled=false) — wrote local digest only.")
        return False
    if not email.get("username") or not email.get("app_password"):
        log("Email enabled but username/app_password missing — skipping send.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email.get("from") or email["username"]
    msg["To"] = email.get("to")
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(email["smtp_host"], int(email["smtp_port"]), timeout=30) as server:
            server.starttls()
            server.login(email["username"], email["app_password"])
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
        log(f"Email digest sent to {email.get('to')}.")
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"Email send FAILED: {type(exc).__name__}: {exc}")
        return False
