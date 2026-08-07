from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IWT AI Sales Platform"
    app_env: str = "local"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "sqlite+pysqlite:///:memory:"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    catalog_api_url: str = ""
    catalog_api_key: str = ""
    catalog_timeout: float = 10.0

    website_api_url: str = ""
    website_api_key: str = ""
    website_api_timeout: float = 10.0
    website_api_auth_mode: str = "none"
    website_catalog_iblock_id: int = 86

    max_bot_token: str = ""
    max_api_base_url: str = "https://platform-api2.max.ru"
    max_api_timeout: float = 10.0
    max_tls_insecure: bool = False

    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_api_base_url: str = "https://graph.facebook.com"
    whatsapp_api_version: str = "v21.0"
    whatsapp_api_timeout: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
