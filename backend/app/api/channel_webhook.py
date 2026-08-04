from app.contracts.channel_adapter import ChannelAdapter
from app.domain.processing import ProcessingResult
from app.services.composition import build_decision_router
from app.services.message_service import MessageService


async def process_channel_webhook(
    adapter: ChannelAdapter,
    payload: dict[str, object],
) -> ProcessingResult:
    """Normalize channel payload and run Freeze pipeline + DecisionRouter."""
    message = await adapter.normalize_incoming(payload)
    service = MessageService(
        decision_router=build_decision_router(
            channel_adapters={message.channel: adapter},
        )
    )
    return await service.process_to_result(message)
