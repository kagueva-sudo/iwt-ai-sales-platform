class WebsiteError(Exception):
    """Base website integration error."""


class WebsiteNotConfiguredError(WebsiteError):
    """Website API is not configured yet."""


class WebsiteTimeoutError(WebsiteError):
    """Website API request timed out."""


class WebsiteUnauthorizedError(WebsiteError):
    """Website API rejected credentials."""


class WebsiteNotFoundError(WebsiteError):
    """Requested website entity was not found."""


class WebsiteServerError(WebsiteError):
    """Website API returned a server-side error."""


class WebsiteUnavailableError(WebsiteError):
    """Website API is unavailable or returned an unexpected response."""
