from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WebsiteStoreConfig:
    base_url: str = "https://www.iwt.ru"
    timeout: float = 15.0
    search_path: str = "/catalog/"
    max_products: int = 8
    enabled: bool = True


def get_website_store_config() -> WebsiteStoreConfig:
    enabled_raw = os.getenv("IWT_STORE_ENABLED", "true").strip().lower()
    enabled = enabled_raw not in {"0", "false", "no", "off"}
    base_url = (os.getenv("IWT_STORE_BASE_URL") or "https://www.iwt.ru").strip().rstrip("/")
    timeout_raw = os.getenv("IWT_STORE_TIMEOUT", "15").strip()
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 15.0
    max_raw = os.getenv("IWT_STORE_MAX_PRODUCTS", "8").strip()
    try:
        max_products = max(1, int(max_raw))
    except ValueError:
        max_products = 8
    return WebsiteStoreConfig(
        base_url=base_url,
        timeout=timeout,
        max_products=max_products,
        enabled=enabled,
    )


def is_website_store_configured() -> bool:
    cfg = get_website_store_config()
    return cfg.enabled and bool(cfg.base_url)