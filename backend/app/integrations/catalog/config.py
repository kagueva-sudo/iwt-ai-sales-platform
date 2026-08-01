from pydantic import BaseModel, AnyHttpUrl

from app.core.config import get_settings


class CatalogConfig(BaseModel):
    api_url: AnyHttpUrl | None = None
    api_key: str = ""
    timeout: float = 10.0


def get_catalog_config() -> CatalogConfig:
    settings = get_settings()
    return CatalogConfig(
        api_url=settings.catalog_api_url or None,
        api_key=settings.catalog_api_key,
        timeout=settings.catalog_timeout,
    )
