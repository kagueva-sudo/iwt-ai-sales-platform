import asyncio
from typing import Any

import httpx

from app.integrations.whatsapp.exceptions import (
    WhatsAppNotConfiguredError,
    WhatsAppRateLimitError,
    WhatsAppUnauthorizedError,
    WhatsAppUnavailableError,
)


class HttpWhatsAppTransport:
    """HTTP transport for Meta WhatsApp Cloud API.

    Sends text via POST /{api-version}/{phone-number-id}/messages.
    """

    RETRYABLE = (WhatsAppRateLimitError, WhatsAppUnavailableError)

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        base_url: str = "https://graph.facebook.com",
        api_version: str = "v21.0",
        timeout: float = 10.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not access_token.strip():
            raise WhatsAppNotConfiguredError("WHATSAPP_ACCESS_TOKEN is required.")
        if not phone_number_id.strip():
            raise WhatsAppNotConfiguredError("WHATSAPP_PHONE_NUMBER_ID is required.")

        self.access_token = access_token.strip()
        self.phone_number_id = phone_number_id.strip()
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version.strip().strip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._owns_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

    async def send_text(self, text: str, *, to: str) -> dict[str, Any]:
        recipient = to.strip()
        if not recipient:
            raise WhatsAppUnavailableError("WhatsApp send requires recipient phone (to).")

        path = f"/{self.api_version}/{self.phone_number_id}/messages"
        return await self._request(
            "POST",
            path,
            json_body={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            },
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self._send(method, path, json_body=json_body)
            except self.RETRYABLE as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * (attempt + 1))
        if last_error is not None:
            raise last_error
        raise WhatsAppUnavailableError("WhatsApp API request failed without a response.")

    async def _send(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            response = await self.http_client.request(
                method,
                path,
                json=json_body,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise WhatsAppUnavailableError("WhatsApp API request timed out.") from exc
        except httpx.RequestError as exc:
            raise WhatsAppUnavailableError("WhatsApp API is unavailable.") from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        status = response.status_code
        if status == 401:
            raise WhatsAppUnauthorizedError("WhatsApp API authorization failed.")
        if status == 429:
            raise WhatsAppRateLimitError("WhatsApp API rate limit exceeded.")
        if status >= 500:
            raise WhatsAppUnavailableError(f"WhatsApp API server error (HTTP {status}).")
        if status >= 400:
            raise WhatsAppUnavailableError(f"WhatsApp API returned HTTP {status}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WhatsAppUnavailableError("WhatsApp API returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            return {"result": payload}
        return payload
