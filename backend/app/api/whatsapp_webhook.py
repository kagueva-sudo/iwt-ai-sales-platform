import logging

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.channel_webhook import process_channel_webhook
from app.api.processing_mappers import map_processing_result_to_ai_response
from app.channel_adapters.whatsapp_payload import (
    extract_whatsapp_text,
    extract_whatsapp_wa_id,
    is_whatsapp_processable_update,
)
from app.integrations.whatsapp.config import get_whatsapp_config
from app.schemas.responses import AIResponseSchema
from app.services.composition import get_whatsapp_adapter

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/channels/whatsapp", tags=["channels-whatsapp"])


@router.get("/webhook")
async def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    """Meta webhook verification handshake."""
    expected = get_whatsapp_config().verify_token.strip()
    if hub_mode == "subscribe" and expected and hub_verify_token == expected and hub_challenge:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed.")


@router.post("/webhook", response_model=AIResponseSchema | None)
async def receive_whatsapp_webhook(payload: dict[str, object]) -> AIResponseSchema | Response:
    # Status / delivery callbacks: acknowledge without running the pipeline.
    if not is_whatsapp_processable_update(payload):
        return Response(content="EVENT_RECEIVED", media_type="text/plain", status_code=200)

    logger.info(
        "WhatsApp inbound from=%s text=%s",
        extract_whatsapp_wa_id(payload),
        (extract_whatsapp_text(payload) or "")[:80],
    )
    try:
        result = await process_channel_webhook(get_whatsapp_adapter(), payload)
    except Exception as exc:
        # Meta retries and may pause webhooks if we return 4xx/5xx.
        logger.exception("WhatsApp pipeline/send failed: %s", exc)
        return Response(content="EVENT_RECEIVED", media_type="text/plain", status_code=200)
    return map_processing_result_to_ai_response(result)
