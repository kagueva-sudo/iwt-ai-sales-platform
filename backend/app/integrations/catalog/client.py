from collections.abc import Mapping
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.integrations.catalog.exceptions import (
    CatalogNotFoundError,
    CatalogServerError,
    CatalogTimeoutError,
    CatalogUnauthorizedError,
    CatalogUnavailableError,
)
from app.integrations.catalog.schemas import (
    CatalogAvailabilityDTO,
    CatalogPriceDTO,
    CatalogProductDTO,
    CatalogSearchResponseDTO,
)

DTO = TypeVar("DTO", bound=BaseModel)


class CatalogApiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.http_client = http_client or httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def search_products(self, query: str, limit: int = 10) -> list[CatalogProductDTO]:
        payload = await self._request("GET", "/products/search", params={"q": query, "limit": limit})
        if isinstance(payload, list):
            payload = {"items": payload}
        return self._validate_response(CatalogSearchResponseDTO, payload).items

    async def get_product(self, product_id: str) -> CatalogProductDTO:
        payload = await self._request("GET", f"/products/{product_id}")
        return self._validate_response(CatalogProductDTO, payload)

    async def get_price(self, product_id: str) -> CatalogPriceDTO:
        payload = await self._request("GET", f"/products/{product_id}/price")
        return self._validate_response(CatalogPriceDTO, payload)

    async def get_availability(self, product_id: str) -> CatalogAvailabilityDTO:
        payload = await self._request("GET", f"/products/{product_id}/availability")
        return self._validate_response(CatalogAvailabilityDTO, payload)

    async def close(self) -> None:
        await self.http_client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        try:
            response = await self.http_client.request(
                method,
                path,
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise CatalogTimeoutError("Catalog API request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 401:
                raise CatalogUnauthorizedError("Catalog API authorization failed.") from exc
            if status_code == 404:
                raise CatalogNotFoundError("Catalog API entity was not found.") from exc
            if status_code >= 500:
                raise CatalogServerError("Catalog API server error.") from exc
            raise CatalogUnavailableError(f"Catalog API returned HTTP {status_code}.") from exc
        except (httpx.RequestError, ValueError) as exc:
            raise CatalogUnavailableError("Catalog API is unavailable or returned invalid data.") from exc

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _validate_response(self, model: type[DTO], payload: Any) -> DTO:
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise CatalogUnavailableError("Catalog API returned invalid data.") from exc
