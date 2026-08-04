from fastapi import APIRouter

from app.api.message_mappers import map_gateway_request_to_message
from app.api.processing_mappers import map_processing_result_to_ai_response
from app.schemas.gateway import GatewayMessageRequest
from app.schemas.responses import AIResponseSchema
from app.services.message_service import MessageService


router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.post("/messages", response_model=AIResponseSchema)
async def receive_gateway_message(payload: GatewayMessageRequest) -> AIResponseSchema:
    message = map_gateway_request_to_message(payload)
    result = await MessageService().process_to_result(message)
    return map_processing_result_to_ai_response(result)
