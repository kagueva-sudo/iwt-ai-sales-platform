import asyncio
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import httpx

from app.integrations.website.exceptions import (
    WebsiteForbiddenError,
    WebsiteNotFoundError,
    WebsiteRateLimitError,
    WebsiteServerError,
    WebsiteTimeoutError,
    WebsiteUnauthorizedError,
    WebsiteUnavailableError,
)

AuthMode = Literal["bearer", "api_key", "none"]
RequestParams = Mapping[str, Any] | Sequence[tuple[str, Any]] | None


class HttpWebsiteTransport:
    """Live HTTP transport for Website / Bitrix webhook API (httpx).

    Auth modes:
    - none: webhook token is already in base_url (Bitrix inbound webhook)
    - bearer: Authorization: Bearer <api_key>
    - api_key: X-API-Key: <api_key>
    """

    RETRYABLE_EXCEPTIONS = (WebsiteTimeoutError, WebsiteRateLimitError, WebsiteServerError)

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 10.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.05,
        auth_mode: AuthMode = "none",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("HttpWebsiteTransport requires a non-empty base_url.")
        if auth_mode not in ("bearer", "api_key", "none"):
            raise ValueError("HttpWebsiteTransport auth_mode must be 'bearer', 'api_key', or 'none'.")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.auth_mode: AuthMode = auth_mode
        self._owns_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        params: RequestParams = None,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self._send(method, path, params)
            except self.RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * (attempt + 1))
        if last_error is not None:
            raise last_error
        raise WebsiteUnavailableError("Website API request failed without a response.")

    async def close(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    async def _send(
        self,
        method: str,
        path: str,
        params: RequestParams,
    ) -> Any:
        try:
            response = await self.http_client.request(
                method,
                path,
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise WebsiteTimeoutError("Website API request timed out.") from exc
        except httpx.RequestError as exc:
            raise WebsiteUnavailableError("Website API is unavailable.") from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> Any:
        status_code = response.status_code
        if status_code == 401:
            raise WebsiteUnauthorizedError("Website API authorization failed.")
        if status_code == 403:
            raise WebsiteForbiddenError("Website API access forbidden.")
        if status_code == 404:
            raise WebsiteNotFoundError("Website API entity was not found.")
        if status_code == 429:
            raise WebsiteRateLimitError("Website API rate limit exceeded.")
        if status_code >= 500:
            raise WebsiteServerError(f"Website API server error (HTTP {status_code}).")
        if status_code >= 400:
            raise WebsiteUnavailableError(f"Website API returned HTTP {status_code}.")

        try:
            return response.json()
        except ValueError as exc:
            raise WebsiteUnavailableError("Website API returned invalid JSON.") from exc

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if not self.api_key or self.auth_mode == "none":
            return headers
        if self.auth_mode == "api_key":
            headers["X-API-Key"] = self.api_key
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
