from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import ValidationError

from app.integrations.website.exceptions import (
    WebsiteNotConfiguredError,
    WebsiteNotFoundError,
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


class WebsiteApiTransport(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Return raw JSON-compatible payload for a future website API."""


class NotConfiguredWebsiteTransport:
    async def request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        raise WebsiteNotConfiguredError(
            "Website API transport is not configured. HTTP integration is reserved for a future sprint."
        )


class WebsiteApiClient:
    """API-ready website client without live HTTP calls in Sprint 4."""

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 10.0,
        transport: WebsiteApiTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport or NotConfiguredWebsiteTransport()

    async def search(self, query: str, limit: int = 10) -> WebsiteSearchResponseDTO:
        payload = await self._request("GET", "/search", params={"q": query, "limit": limit})
        return self._validate(WebsiteSearchResponseDTO, payload)

    async def get_product_by_sku(self, sku: str) -> WebsiteProductDTO:
        payload = await self._request("GET", f"/products/by-sku/{sku}")
        return self._validate(WebsiteProductDTO, payload)

    async def get_delivery_info(self) -> WebsiteCompanyInfoDTO:
        payload = await self._request("GET", "/info/delivery")
        return self._validate(WebsiteCompanyInfoDTO, payload)

    async def get_payment_info(self) -> WebsiteCompanyInfoDTO:
        payload = await self._request("GET", "/info/payment")
        return self._validate(WebsiteCompanyInfoDTO, payload)

    async def get_warranty_info(self) -> WebsiteCompanyInfoDTO:
        payload = await self._request("GET", "/info/warranty")
        return self._validate(WebsiteCompanyInfoDTO, payload)

    async def get_contacts(self) -> WebsiteContactInfoDTO:
        payload = await self._request("GET", "/info/contacts")
        return self._validate(WebsiteContactInfoDTO, payload)

    async def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        try:
            return await self.transport.request(method, path, params)
        except (
            WebsiteNotConfiguredError,
            WebsiteTimeoutError,
            WebsiteUnauthorizedError,
            WebsiteNotFoundError,
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
