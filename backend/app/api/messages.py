from fastapi import APIRouter

from app.api.message_mappers import map_incoming_request_to_message
from app.api.response_mappers import map_message_to_ai_response
from app.schemas.messages import IncomingMessageRequest
from app.schemas.responses import AIResponseSchema
from app.services.message_service import MessageService


router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/incoming", response_model=AIResponseSchema)
async def receive_message(payload: IncomingMessageRequest) -> AIResponseSchema:
    message = map_incoming_request_to_message(payload)
    response_message = await MessageService().process_message(message)
    return map_message_to_ai_response(response_message)
