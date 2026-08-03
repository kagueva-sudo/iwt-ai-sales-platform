from pydantic import AnyHttpUrl, BaseModel

from app.core.config import get_settings


class WebsiteConfig(BaseModel):
    api_url: AnyHttpUrl | None = None
    api_key: str = ""
    timeout: float = 10.0


def get_website_config() -> WebsiteConfig:
    settings = get_settings()
    return WebsiteConfig(
        api_url=settings.website_api_url or None,
        api_key=settings.website_api_key,
        timeout=settings.website_api_timeout,
    )
