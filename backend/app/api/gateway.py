from fastapi import APIRouter

from app.api.message_mappers import map_gateway_request_to_message
from app.api.response_mappers import map_message_to_ai_response
from app.schemas.gateway import GatewayMessageRequest
from app.schemas.responses import AIResponseSchema
from app.services.message_service import MessageService


router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.post("/messages", response_model=AIResponseSchema)
async def receive_gateway_message(payload: GatewayMessageRequest) -> AIResponseSchema:
    message = map_gateway_request_to_message(payload)
    response_message = await MessageService().process_message(message)
    return map_message_to_ai_response(response_message)
