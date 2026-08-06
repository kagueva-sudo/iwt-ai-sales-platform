from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from app.integrations.website.bitrix_mapper import (
    extract_bitrix_price,
    extract_bitrix_product,
    extract_bitrix_products,
    map_bitrix_product_to_dto,
)
from app.integrations.website.exceptions import (
    WebsiteForbiddenError,
    WebsiteNotConfiguredError,
    WebsiteNotFoundError,
    WebsiteRateLimitError,
    WebsiteServerError,
    WebsiteTimeoutError,
    WebsiteUnauthorizedError,
    WebsiteUnavailableError,
)
from app.integrations.website.schemas import (
    WebsiteCompanyInfoDTO,
    WebsiteContactInfoDTO,
    WebsiteProductDTO,
    WebsiteSearchResponseDTO,
)
from app.integrations.website.transport import AuthMode, HttpWebsiteTransport

RequestParams = Mapping[str, Any] | Sequence[tuple[str, Any]] | None


class WebsiteApiTransport(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        params: RequestParams = None,
    ) -> Any:
        """Return raw JSON-compatible payload for website/Bitrix API."""


class NotConfiguredWebsiteTransport:
    async def request(
        self,
        method: str,
        path: str,
        params: RequestParams = None,
    ) -> Any:
        raise WebsiteNotConfiguredError(
            "Website API transport is not configured. Set WEBSITE_API_URL to the Bitrix webhook base."
        )


class WebsiteApiClient:
    """Bitrix REST catalog client (iwt.ru webhook) for product data only.

    Bitrix scope: product, price, stock, characteristics.
    Knowledge Base scope: payment, delivery, warranty, company, FAQ.

    Search resolves products by Bitrix id, code, xmlId, and name substring.
    Product.sku is mapped from Bitrix `code`.
    Price is loaded from catalog.price.list (not present on product.get).
    """

    PRODUCT_SELECT = (
        "id",
        "iblockId",
        "name",
        "code",
        "xmlId",
        "quantity",
        "available",
        "previewText",
        "detailText",
        "iblockSectionId",
    )

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 10.0,
        auth_mode: AuthMode | Literal["bearer", "api_key", "none"] = "none",
        transport: WebsiteApiTransport | None = None,
        iblock_id: int = 86,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.iblock_id = iblock_id
        if auth_mode == "api_key":
            self.auth_mode: AuthMode = "api_key"
        elif auth_mode == "bearer":
            self.auth_mode = "bearer"
        else:
            self.auth_mode = "none"

        if transport is not None:
            self.transport = transport
        elif self.base_url:
            self.transport = HttpWebsiteTransport(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
                auth_mode=self.auth_mode,
            )
        else:
            self.transport = NotConfiguredWebsiteTransport()

    async def search(self, query: str, limit: int = 10) -> WebsiteSearchResponseDTO:
        cleaned = query.strip()
        if not cleaned:
            return WebsiteSearchResponseDTO()

        found: dict[str, dict[str, Any]] = {}

        if cleaned.isdigit():
            product = await self._get_raw_by_id(int(cleaned))
            if product is not None:
                found[str(product.get("id"))] = product

        for product in await self._list_by_filter({"code": cleaned}, limit=limit):
            found[str(product.get("id"))] = product
        for product in await self._list_by_filter({"xmlId": cleaned}, limit=limit):
            found[str(product.get("id"))] = product
        for product in await self._list_by_filter({"%name": cleaned}, limit=limit):
            found[str(product.get("id"))] = product

        products: list[WebsiteProductDTO] = []
        for product in list(found.values())[: max(1, limit)]:
            price_row = await self._get_price_row(product.get("id"))
            products.append(map_bitrix_product_to_dto(product, price_row))
        return WebsiteSearchResponseDTO(products=products)

    async def get_product_by_sku(self, sku: str) -> WebsiteProductDTO:
        cleaned = sku.strip()
        if not cleaned:
            raise WebsiteNotFoundError("Product identifier is empty.")

        product: dict[str, Any] | None = None
        if cleaned.isdigit():
            product = await self._get_raw_by_id(int(cleaned))
        if product is None:
            matches = await self._list_by_filter({"code": cleaned}, limit=1)
            product = matches[0] if matches else None
        if product is None:
            matches = await self._list_by_filter({"xmlId": cleaned}, limit=1)
            product = matches[0] if matches else None
        if product is None:
            raise WebsiteNotFoundError(f"Product '{cleaned}' was not found.")

        product_id = product.get("id")
        if product_id is not None:
            full = await self._get_raw_by_id(int(product_id))
            if full is not None:
                product = full

        price_row = await self._get_price_row(product.get("id"))
        return map_bitrix_product_to_dto(product, price_row)

    async def get_delivery_info(self) -> WebsiteCompanyInfoDTO:
        # Delivery texts live in Knowledge Base, not Bitrix catalog.
        raise WebsiteNotFoundError("Delivery info is served by Knowledge Base, not Bitrix.")

    async def get_payment_info(self) -> WebsiteCompanyInfoDTO:
        # Payment texts live in Knowledge Base, not Bitrix catalog.
        raise WebsiteNotFoundError("Payment info is served by Knowledge Base, not Bitrix.")

    async def get_warranty_info(self) -> WebsiteCompanyInfoDTO:
        # Warranty texts live in Knowledge Base, not Bitrix catalog.
        raise WebsiteNotFoundError("Warranty info is served by Knowledge Base, not Bitrix.")

    async def get_contacts(self) -> WebsiteContactInfoDTO:
        # Company/contacts live in Knowledge Base, not Bitrix catalog.
        raise WebsiteNotFoundError("Contacts are served by Knowledge Base, not Bitrix.")

    async def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if close is not None:
            await close()

    async def _get_raw_by_id(self, product_id: int) -> dict[str, Any] | None:
        try:
            payload = await self._bitrix("catalog.product.get", {"id": product_id})
        except WebsiteNotFoundError:
            return None
        return extract_bitrix_product(payload)

    async def _list_by_filter(self, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        params: list[tuple[str, Any]] = [
            ("filter[iblockId]", self.iblock_id),
            ("start", 0),
        ]
        for key, value in filters.items():
            params.append((f"filter[{key}]", value))
        for field in self.PRODUCT_SELECT:
            params.append(("select[]", field))

        payload = await self._bitrix("catalog.product.list", params)
        products = extract_bitrix_products(payload)
        return products[: max(1, limit)]

    async def _get_price_row(self, product_id: Any) -> dict[str, Any] | None:
        if product_id is None:
            return None
        try:
            payload = await self._bitrix(
                "catalog.price.list",
                {"filter[productId]": product_id},
            )
        except WebsiteNotFoundError:
            return None
        return extract_bitrix_price(payload)

    async def _bitrix(self, method: str, params: RequestParams = None) -> Any:
        payload = await self._request("GET", f"/{method}.json", params=params)
        if not isinstance(payload, dict):
            raise WebsiteUnavailableError("Website API returned invalid data.")
        if payload.get("error"):
            error_code = str(payload.get("error"))
            description = str(payload.get("error_description") or error_code)
            if error_code in {"ACCESS_DENIED", "invalid_credentials", "WRONG_AUTH"}:
                raise WebsiteUnauthorizedError(description)
            if "not found" in description.lower() or error_code.endswith("_NOT_FOUND"):
                raise WebsiteNotFoundError(description)
            raise WebsiteUnavailableError(description)
        return payload.get("result", payload)

    async def _request(
        self,
        method: str,
        path: str,
        params: RequestParams = None,
    ) -> Any:
        try:
            return await self.transport.request(method, path, params)
        except (
            WebsiteNotConfiguredError,
            WebsiteTimeoutError,
            WebsiteUnauthorizedError,
            WebsiteForbiddenError,
            WebsiteNotFoundError,
            WebsiteRateLimitError,
            WebsiteServerError,
            WebsiteUnavailableError,
        ):
            raise
        except TimeoutError as exc:
            raise WebsiteTimeoutError("Website API request timed out.") from exc
        except Exception as exc:
            raise WebsiteUnavailableError("Website API is unavailable or returned invalid data.") from exc

    def _validate(self, model: type, payload: Any):
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise WebsiteUnavailableError("Website API returned invalid data.") from exc
