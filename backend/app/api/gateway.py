from fastapi import APIRouter

from app.api.response_mappers import map_message_to_ai_response
from app.gateway.gateway_service import GatewayService
from app.schemas.gateway import GatewayMessageRequest
from app.schemas.responses import AIResponseSchema
from app.services.message_service import MessageService


router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.post("/messages", response_model=AIResponseSchema)
async def receive_gateway_message(payload: GatewayMessageRequest) -> AIResponseSchema:
    normalized_message = GatewayService().normalize(payload)
    response_message = await MessageService().process_incoming_message(normalized_message)
    return map_message_to_ai_response(response_message)
