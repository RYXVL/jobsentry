"""Alert emails, sent through the SMTP server set in backend/.env
(JOBSENTRY_SMTP_*). Uses Python's built-in smtplib.

fingerprint() identifies the current mail settings plus a recipient. The
monitor marks an address "verified" only after a test email reached it,
and a different fingerprint (new settings or address) means testing again.
"""

from __future__ import annotations

import hashlib
import smtplib
import ssl
from email.message import EmailMessage

from ..config import Settings
from ..core.exceptions import JobsentryError

class EmailError(JobsentryError):
    """An email couldn't be sent (shown as a 502 with the reason)."""

def is_configured(settings: Settings) -> bool:
    """True if backend/.env has at least a mail server and a sender."""
    return bool(settings.smtp_host and settings.smtp_from)

def fingerprint(settings: Settings, email_to: str) -> str:
    """A hash of the mail settings and recipient (the password included, as
    a hash), so any change requires a new test email."""
    parts = [
        settings.smtp_host, str(settings.smtp_port), settings.smtp_security,
        settings.smtp_username, settings.smtp_from, email_to.strip().lower(),
        hashlib.sha256(settings.smtp_password.encode()).hexdigest(),
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()

def send_email(settings: Settings, to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send one email, or raise EmailError explaining what went wrong."""
    if not is_configured(settings):
        raise EmailError(
            "Email isn't set up: add JOBSENTRY_SMTP_HOST and JOBSENTRY_SMTP_FROM "
            "(and usually a username and password) to backend/.env, then restart the API."
        )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    timeout = settings.http_timeout
    context = ssl.create_default_context()
    try:
        if settings.smtp_security == "ssl":
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=timeout, context=context
            )
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)
        with server:
            if settings.smtp_security == "starttls":
                server.starttls(context=context)
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise EmailError(
            "The mail server rejected the username or password. Gmail and Outlook "
            "need an app password, not your normal password."
        ) from None
    except smtplib.SMTPRecipientsRefused:
        raise EmailError(f"The mail server refused the address {to}.") from None
    except (smtplib.SMTPException, OSError) as e:
        raise EmailError(
            f"Couldn't send email through {settings.smtp_host}:{settings.smtp_port}: {e}"
        ) from None