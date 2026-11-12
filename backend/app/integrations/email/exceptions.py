class EmailError(Exception):
    """Base email integration error."""


class EmailNotConfiguredError(EmailError):
    """IMAP/SMTP credentials are missing."""


class EmailTransportError(EmailError):
    """IMAP/SMTP transport failure."""
