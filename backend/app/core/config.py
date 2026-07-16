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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
