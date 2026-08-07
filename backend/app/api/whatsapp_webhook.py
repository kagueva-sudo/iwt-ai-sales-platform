from fastapi import APIRouter, HTTPException, Query, Response

from app.api.channel_webhook import process_channel_webhook
from app.api.processing_mappers import map_processing_result_to_ai_response
from app.channel_adapters.whatsapp_payload import is_whatsapp_processable_update
from app.core.errors import ProviderError
from app.integrations.whatsapp.config import get_whatsapp_config
from app.schemas.responses import AIResponseSchema
from app.services.composition import get_whatsapp_adapter


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

    try:
        result = await process_channel_webhook(get_whatsapp_adapter(), payload)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return map_processing_result_to_ai_response(result)
