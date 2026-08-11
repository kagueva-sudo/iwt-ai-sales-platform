import sys

from pydantic import AnyHttpUrl, BaseModel

from app.core.config import get_settings


class MaxConfig(BaseModel):
    bot_token: str = ""
    api_base_url: AnyHttpUrl = "https://platform-api2.max.ru"  # type: ignore[assignment]
    timeout: float = 10.0
    tls_insecure: bool = False


def get_max_config() -> MaxConfig:
    settings = get_settings()
    base = settings.max_api_base_url.strip() or "https://platform-api2.max.ru"
    return MaxConfig(
        bot_token=settings.max_bot_token,
        api_base_url=base,  # type: ignore[arg-type]
        timeout=settings.max_api_timeout,
        tls_insecure=settings.max_tls_insecure,
    )


def is_max_configured() -> bool:
    # Prevent real outbound calls during pytest runs.
    # Tests should use stubs/adapters and not depend on external MAX connectivity.
    if "pytest" in sys.modules:
        return False
    return bool(get_settings().max_bot_token.strip())
