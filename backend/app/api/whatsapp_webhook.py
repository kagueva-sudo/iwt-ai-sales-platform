from fastapi import APIRouter, HTTPException

from app.api.channel_webhook import process_channel_webhook
from app.api.processing_mappers import map_processing_result_to_ai_response
from app.core.errors import ProviderError
from app.schemas.responses import AIResponseSchema
from app.services.composition import get_whatsapp_adapter


router = APIRouter(prefix="/channels/whatsapp", tags=["channels-whatsapp"])


@router.post("/webhook", response_model=AIResponseSchema)
async def receive_whatsapp_webhook(payload: dict[str, object]) -> AIResponseSchema:
    try:
        result = await process_channel_webhook(get_whatsapp_adapter(), payload)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return map_processing_result_to_ai_response(result)
