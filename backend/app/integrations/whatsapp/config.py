from pydantic import AnyHttpUrl, BaseModel

from app.core.config import get_settings


class WhatsAppConfig(BaseModel):
    access_token: str = ""
    phone_number_id: str = ""
    verify_token: str = ""
    api_base_url: AnyHttpUrl = "https://graph.facebook.com"  # type: ignore[assignment]
    api_version: str = "v21.0"
    timeout: float = 10.0


def get_whatsapp_config() -> WhatsAppConfig:
    settings = get_settings()
    base = settings.whatsapp_api_base_url.strip() or "https://graph.facebook.com"
    version = settings.whatsapp_api_version.strip() or "v21.0"
    return WhatsAppConfig(
        access_token=settings.whatsapp_access_token,
        phone_number_id=settings.whatsapp_phone_number_id,
        verify_token=settings.whatsapp_verify_token,
        api_base_url=base,  # type: ignore[arg-type]
        api_version=version,
        timeout=settings.whatsapp_api_timeout,
    )


def is_whatsapp_configured() -> bool:
    settings = get_settings()
    return bool(settings.whatsapp_access_token.strip() and settings.whatsapp_phone_number_id.strip())
