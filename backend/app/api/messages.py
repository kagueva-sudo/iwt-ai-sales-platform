from fastapi import APIRouter

from app.api.message_mappers import map_incoming_request_to_message
from app.api.processing_mappers import map_processing_result_to_ai_response
from app.schemas.messages import IncomingMessageRequest
from app.schemas.responses import AIResponseSchema
from app.services.message_service import MessageService


router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/incoming", response_model=AIResponseSchema)
async def receive_message(payload: IncomingMessageRequest) -> AIResponseSchema:
    message = map_incoming_request_to_message(payload)
    result = await MessageService().process_to_result(message)
    return map_processing_result_to_ai_response(result)
