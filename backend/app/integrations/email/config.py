from pydantic import BaseModel

from app.core.config import get_settings


class EmailConfig(BaseModel):
    enabled: bool = False
    imap_host: str = "imap.yandex.ru"
    imap_port: int = 993
    smtp_host: str = "smtp.yandex.ru"
    smtp_port: int = 465
    username: str = ""
    password: str = ""
    mail_from: str = ""
    poll_seconds: int = 60
    mailbox: str = "INBOX"


def get_email_config() -> EmailConfig:
    settings = get_settings()
    mail_from = settings.email_from.strip() or settings.email_username.strip()
    return EmailConfig(
        enabled=settings.email_enabled,
        imap_host=settings.email_imap_host.strip() or "imap.yandex.ru",
        imap_port=settings.email_imap_port,
        smtp_host=settings.email_smtp_host.strip() or "smtp.yandex.ru",
        smtp_port=settings.email_smtp_port,
        username=settings.email_username.strip(),
        password=settings.email_password,
        mail_from=mail_from,
        poll_seconds=max(15, settings.email_poll_seconds),
        mailbox=settings.email_mailbox.strip() or "INBOX",
    )


def is_email_configured() -> bool:
    config = get_email_config()
    return bool(
        config.enabled
        and config.username
        and config.password
        and config.mail_from
    )
