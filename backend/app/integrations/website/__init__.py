"""Website API integration layer.

Live HTTP is enabled when WEBSITE_API_URL is set: WebsiteApiClient then uses
HttpWebsiteTransport with Bearer or X-API-Key auth.
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
