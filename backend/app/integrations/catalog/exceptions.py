class CatalogError(Exception):
    """Base catalog integration error."""


class CatalogTimeoutError(CatalogError):
    """Catalog API request timed out."""


class CatalogUnauthorizedError(CatalogError):
    """Catalog API rejected credentials."""


class CatalogNotFoundError(CatalogError):
    """Requested catalog entity was not found."""


class CatalogServerError(CatalogError):
    """Catalog API returned a server-side error."""


class CatalogUnavailableError(CatalogError):
    """Catalog API is unavailable or returned an unexpected response."""
