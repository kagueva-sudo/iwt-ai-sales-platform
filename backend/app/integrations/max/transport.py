import asyncio
from typing import Any

import httpx

from app.integrations.max.exceptions import (
    MaxNotConfiguredError,
    MaxRateLimitError,
    MaxUnauthorizedError,
    MaxUnavailableError,
)


class HttpMaxTransport:
    """HTTP transport for MAX Bot API (platform-api2.max.ru).

    Sends text messages via POST /messages with user_id or chat_id query param.
    """

    RETRYABLE = (MaxRateLimitError, MaxUnavailableError)

    def __init__(
        self,
        bot_token: str,
        base_url: str = "https://platform-api2.max.ru",
        timeout: float = 10.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.2,
        http_client: httpx.AsyncClient | None = None,
        verify_tls: bool = True,
    ) -> None:
        if not bot_token.strip():
            raise MaxNotConfiguredError("MAX_BOT_TOKEN is required for HttpMaxTransport.")

        self.bot_token = bot_token.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._owns_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify_tls,
        )

    async def send_text(
        self,
        text: str,
        *,
        user_id: str | None = None,
        chat_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if chat_id:
            params["chat_id"] = chat_id
        elif user_id:
            params["user_id"] = user_id
        else:
            raise MaxUnavailableError("MAX send requires user_id or chat_id.")

        return await self._request(
            "POST",
            "/messages",
            params=params,
            json_body={"text": text},
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self._send(method, path, params=params, json_body=json_body)
            except self.RETRYABLE as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * (attempt + 1))
        if last_error is not None:
            raise last_error
        raise MaxUnavailableError("MAX API request failed without a response.")

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None,
        json_body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            response = await self.http_client.request(
                method,
                path,
                params=params,
                json=json_body,
                headers={
                    "Authorization": self.bot_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise MaxUnavailableError("MAX API request timed out.") from exc
        except httpx.RequestError as exc:
            raise MaxUnavailableError("MAX API is unavailable.") from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        status = response.status_code
        if status == 401:
            raise MaxUnauthorizedError("MAX API authorization failed.")
        if status == 429:
            raise MaxRateLimitError("MAX API rate limit exceeded.")
        if status >= 500:
            raise MaxUnavailableError(f"MAX API server error (HTTP {status}).")
        if status >= 400:
            raise MaxUnavailableError(f"MAX API returned HTTP {status}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise MaxUnavailableError("MAX API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            return {"result": payload}
        return payload
