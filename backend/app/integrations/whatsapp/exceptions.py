class WhatsAppError(Exception):
    """Base WhatsApp Cloud API error."""


class WhatsAppNotConfiguredError(WhatsAppError):
    """WhatsApp credentials are not configured."""


class WhatsAppUnauthorizedError(WhatsAppError):
    """WhatsApp API rejected credentials."""


class WhatsAppRateLimitError(WhatsAppError):
    """WhatsApp API rate limit exceeded."""


class WhatsAppUnavailableError(WhatsAppError):
    """WhatsApp API is unavailable or returned an unexpected response."""
