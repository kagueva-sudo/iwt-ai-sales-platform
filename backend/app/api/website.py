from fastapi import APIRouter, HTTPException

from app.api.channel_webhook import process_channel_webhook
from app.api.processing_mappers import map_processing_result_to_ai_response
from app.core.errors import ProviderError
from app.schemas.responses import AIResponseSchema
from app.services.composition import get_website_chat_adapter, get_website_form_adapter


router = APIRouter(prefix="/channels/website", tags=["channels-website"])


@router.post("/form", response_model=AIResponseSchema)
async def receive_website_form(payload: dict[str, object]) -> AIResponseSchema:
    try:
        result = await process_channel_webhook(get_website_form_adapter(), payload)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return map_processing_result_to_ai_response(result)


@router.post("/chat", response_model=AIResponseSchema)
async def receive_website_chat(payload: dict[str, object]) -> AIResponseSchema:
    try:
        result = await process_channel_webhook(get_website_chat_adapter(), payload)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return map_processing_result_to_ai_response(result)
