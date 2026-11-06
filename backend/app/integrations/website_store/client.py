from __future__ import annotations

import html as htmlmod
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin

import httpx

from app.integrations.website_store.config import WebsiteStoreConfig, get_website_store_config

logger = logging.getLogger(__name__)

_TITLE_RE = re.compile(
    r'<a href="([^"]+)" title="([^"]*)" class="name font-title">([^<]*)</a>',
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r'id="[^"]*_price">\s*([\d\s\u00a0]+)\s*руб', re.IGNORECASE)
_SKU_RE = re.compile(r'id="bx_\d+_(\d+)_')
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class StoreProductDTO:
    sku: str
    name: str
    url: str
    price: float | None = None
    currency: str = "RUB"


class WebsiteStoreClient:
    """Fetches product cards from the public iwt.ru catalog search page."""

    def __init__(
        self,
        config: WebsiteStoreConfig | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or get_website_store_config()
        self._owns_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; IWT-AI-Assistant/1.0; +https://www.iwt.ru)"
                ),
                "Accept-Language": "ru-RU,ru;q=0.9",
            },
            follow_redirects=True,
        )

    async def search_products(self, query: str, limit: int | None = None) -> list[StoreProductDTO]:
        q = (query or "").strip()
        if not q:
            return []
        limit = limit or self.config.max_products
        url = f"{self.config.base_url}{self.config.search_path}?q={quote_plus(q)}"
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            html = response.text
        except httpx.HTTPError as exc:
            logger.warning("iwt.ru store search failed: %s", exc)
            return []
        products = self.parse_catalog_html(html, base_url=self.config.base_url)
        return products[: max(1, limit)]

    async def close(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    @staticmethod
    def parse_catalog_html(html: str, *, base_url: str = "https://www.iwt.ru") -> list[StoreProductDTO]:
        products: list[StoreProductDTO] = []
        seen: set[str] = set()
        for match in _TITLE_RE.finditer(html or ""):
            href = match.group(1).strip()
            title_attr = htmlmod.unescape(match.group(2) or "").strip()
            title_body = htmlmod.unescape(match.group(3) or "").strip()
            name = _SPACE_RE.sub(" ", title_attr or title_body).strip()
            if not name or not href:
                continue
            absolute_url = urljoin(base_url.rstrip("/") + "/", href.lstrip("/"))
            start = max(0, match.start() - 1500)
            chunk = html[start : match.start()]
            price: float | None = None
            prices = _PRICE_RE.findall(chunk)
            if prices:
                raw = prices[-1].replace("\xa0", "").replace(" ", "")
                try:
                    price = float(raw)
                except ValueError:
                    price = None
            sku_matches = _SKU_RE.findall(chunk)
            sku = sku_matches[-1] if sku_matches else absolute_url.rstrip("/").split("/")[-1]
            dedupe_key = sku or absolute_url
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            products.append(
                StoreProductDTO(
                    sku=str(sku),
                    name=name,
                    url=absolute_url,
                    price=price,
                )
            )
        return products