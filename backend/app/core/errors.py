class AppError(Exception):
    """Base application error."""


class ProviderError(AppError):
    """External or internal provider failed."""


class ValidationError(AppError):
    """AI response cannot be safely sent to a client."""
