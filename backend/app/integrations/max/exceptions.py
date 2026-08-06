class MaxError(Exception):
    """Base MAX API error."""


class MaxNotConfiguredError(MaxError):
    """MAX bot token is not configured."""


class MaxUnauthorizedError(MaxError):
    """MAX API rejected credentials."""


class MaxRateLimitError(MaxError):
    """MAX API rate limit exceeded."""


class MaxUnavailableError(MaxError):
    """MAX API is unavailable or returned an unexpected response."""
