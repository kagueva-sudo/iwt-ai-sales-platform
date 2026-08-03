from app.core.constants import AIValidationStatus, ProcessingStatus
from app.domain.messages import Message
from app.schemas.responses import AIResponseSchema


def map_message_to_ai_response(message: Message) -> AIResponseSchema:
    validation_status = (
        AIValidationStatus.HANDOFF_REQUIRED
        if message.status == ProcessingStatus.HANDOFF_REQUIRED
        else AIValidationStatus.APPROVED
    )
    return AIResponseSchema(
        text=message.text,
        validation_status=validation_status,
        sources=[],
        handoff_required=message.status == ProcessingStatus.HANDOFF_REQUIRED,
    )
