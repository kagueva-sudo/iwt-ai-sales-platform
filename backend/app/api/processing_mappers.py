from app.core.constants import AIValidationStatus, MessageDirection, ProcessingStatus
from app.domain.messages import Message
from app.domain.processing import ProcessingDecision, ProcessingResult
from app.schemas.responses import AIResponseSchema


def map_processing_result_to_message(result: ProcessingResult, inbound: Message) -> Message:
    if result.decision == ProcessingDecision.RESPOND:
        status = ProcessingStatus.PROCESSED
    elif result.decision == ProcessingDecision.ERROR:
        status = ProcessingStatus.FAILED
    else:
        status = ProcessingStatus.HANDOFF_REQUIRED

    return Message(
        text=result.response_text or "",
        channel=result.channel or inbound.channel,
        direction=MessageDirection.OUTBOUND,
        customer_id=result.customer_name or inbound.customer_id,
        customer_contact=result.customer_contact or inbound.customer_contact,
        status=status,
    )


def map_processing_result_to_ai_response(result: ProcessingResult) -> AIResponseSchema:
    if result.decision == ProcessingDecision.RESPOND:
        validation_status = AIValidationStatus.APPROVED
        handoff_required = False
    elif result.decision == ProcessingDecision.NEEDS_MORE_DATA:
        validation_status = AIValidationStatus.NEEDS_DATA
        handoff_required = True
    else:
        validation_status = AIValidationStatus.HANDOFF_REQUIRED
        handoff_required = True

    return AIResponseSchema(
        text=result.response_text or "",
        validation_status=validation_status,
        sources=list(result.sources),
        handoff_required=handoff_required,
        reason=result.metadata.get("reason")
        or (result.handoff_reason.value if result.handoff_reason else None)
        or ("|".join(result.errors) if result.errors else None),
    )
