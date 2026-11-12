from app.integrations.email.config import EmailConfig, get_email_config, is_email_configured
from app.integrations.email.imap_client import ImapEmailClient
from app.integrations.email.schemas import InboundEmail
from app.integrations.email.smtp_client import SmtpEmailClient

__all__ = [
    "EmailConfig",
    "ImapEmailClient",
    "InboundEmail",
    "SmtpEmailClient",
    "get_email_config",
    "is_email_configured",
]
