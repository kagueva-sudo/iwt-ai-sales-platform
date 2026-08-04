from collections.abc import Mapping
from typing import Any, Literal, Protocol

from pydantic import ValidationError

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


class WebsiteApiTransport(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Return raw JSON-compatible payload for website API."""


class NotConfiguredWebsiteTransport:
    async def request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        raise WebsiteNotConfiguredError(
            "Website API transport is not configured. Set WEBSITE_API_URL to enable HttpWebsiteTransport."
        )


class WebsiteApiClient:
    """Website API client.

    When base_url is provided and transport is omitted, uses live HttpWebsiteTransport.
    Without base_url, keeps NotConfiguredWebsiteTransport (safe default for local/tests).
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 10.0,
        auth_mode: AuthMode | Literal["bearer", "api_key"] = "bearer",
        transport: WebsiteApiTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.auth_mode: AuthMode = "api_key" if auth_mode == "api_key" else "bearer"
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

    async def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if close is not None:
            await close()

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
