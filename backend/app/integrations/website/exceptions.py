class WebsiteError(Exception):
    """Base website integration error."""


class WebsiteNotConfiguredError(WebsiteError):
    """Website API is not configured yet."""


class WebsiteTimeoutError(WebsiteError):
    """Website API request timed out."""


class WebsiteUnauthorizedError(WebsiteError):
    """Website API rejected credentials (401)."""


class WebsiteForbiddenError(WebsiteError):
    """Website API denied access (403)."""


class WebsiteNotFoundError(WebsiteError):
    """Requested website entity was not found (404)."""


class WebsiteRateLimitError(WebsiteError):
    """Website API rate limit exceeded (429)."""


class WebsiteServerError(WebsiteError):
    """Website API returned a server-side error (5xx)."""


class WebsiteUnavailableError(WebsiteError):
    """Website API is unavailable or returned an unexpected response."""
