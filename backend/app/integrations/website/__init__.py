"""Website / Bitrix catalog integration.

Set WEBSITE_API_URL to the Bitrix webhook base (`https://iwt.ru/rest/1/<code>`).
Auth mode `none`: token is part of the URL path.
"""

from app.integrations.website.client import NotConfiguredWebsiteTransport, WebsiteApiClient
from app.integrations.website.config import build_website_api_client, is_website_api_configured
from app.integrations.website.transport import HttpWebsiteTransport

__all__ = [
    "HttpWebsiteTransport",
    "NotConfiguredWebsiteTransport",
    "WebsiteApiClient",
    "build_website_api_client",
    "is_website_api_configured",
]
