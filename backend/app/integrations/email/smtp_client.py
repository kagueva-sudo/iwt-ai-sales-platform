"""SMTP client for manager replies (Yandex-compatible)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.integrations.email.config import EmailConfig
from app.integrations.email.exceptions import EmailNotConfiguredError, EmailTransportError


class SmtpEmailClient:
    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def send(
        self,
        *,
        to_address: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> None:
        if not self.config.username or not self.config.password or not self.config.mail_from:
            raise EmailNotConfiguredError("EMAIL SMTP credentials are required.")
        if not to_address.strip():
            raise EmailTransportError("SMTP recipient is empty.")

        message = EmailMessage()
        message["From"] = self.config.mail_from
        message["To"] = to_address.strip()
        message["Subject"] = subject.strip() or "Re: IWT"
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = references or in_reply_to
        message.set_content(body)

        try:
            if self.config.smtp_port == 465:
                with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, timeout=30) as smtp:
                    smtp.login(self.config.username, self.config.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=30) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(self.config.username, self.config.password)
                    smtp.send_message(message)
        except EmailNotConfiguredError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EmailTransportError(f"SMTP send failed: {exc}") from exc
