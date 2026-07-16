from fastapi import APIRouter

from app.core.constants import AIValidationStatus, ProcessingStatus
from app.schemas.messages import IncomingMessageRequest
from app.schemas.responses import AIResponseSchema
from app.services.message_service import MessageService


router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/incoming", response_model=AIResponseSchema)
async def receive_message(payload: IncomingMessageRequest) -> AIResponseSchema:
    response_message = await MessageService().process_incoming_message(payload)
    validation_status = (
        AIValidationStatus.HANDOFF_REQUIRED
        if response_message.status == ProcessingStatus.HANDOFF_REQUIRED
        else AIValidationStatus.APPROVED
    )
    return AIResponseSchema(
        text=response_message.text,
        validation_status=validation_status,
        sources=[],
        handoff_required=response_message.status == ProcessingStatus.HANDOFF_REQUIRED,
    )
