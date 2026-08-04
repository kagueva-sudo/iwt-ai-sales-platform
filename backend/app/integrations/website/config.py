from pydantic import AnyHttpUrl, BaseModel, field_validator

from app.core.config import get_settings
from app.integrations.website.client import WebsiteApiClient
from app.integrations.website.transport import AuthMode


class WebsiteConfig(BaseModel):
    api_url: AnyHttpUrl | None = None
    api_key: str = ""
    timeout: float = 10.0
    auth_mode: AuthMode = "bearer"

    @field_validator("auth_mode", mode="before")
    @classmethod
    def normalize_auth_mode(cls, value: object) -> str:
        text = str(value or "bearer").strip().lower()
        if text in {"api_key", "apikey", "x-api-key"}:
            return "api_key"
        return "bearer"


def get_website_config() -> WebsiteConfig:
    settings = get_settings()
    return WebsiteConfig(
        api_url=settings.website_api_url or None,
        api_key=settings.website_api_key,
        timeout=settings.website_api_timeout,
        auth_mode=settings.website_api_auth_mode,
    )


def is_website_api_configured() -> bool:
    return bool(str(get_settings().website_api_url or "").strip())


def build_website_api_client() -> WebsiteApiClient:
    """Build client with live HttpWebsiteTransport when WEBSITE_API_URL is set."""
    config = get_website_config()
    return WebsiteApiClient(
        base_url=str(config.api_url) if config.api_url else "",
        api_key=config.api_key,
        timeout=config.timeout,
        auth_mode=config.auth_mode,
    )
