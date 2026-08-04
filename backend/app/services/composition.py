from app.ai_core.core import AICore
from app.ai_core.openai_provider import OpenAIProvider
from app.ai_core.validator import AIValidator
from app.channel_adapters.email_adapter import EmailChannelAdapter
from app.channel_adapters.max_adapter import MaxChannelAdapter
from app.channel_adapters.website_chat_adapter import WebsiteChatAdapter
from app.channel_adapters.website_form_adapter import WebsiteFormAdapter
from app.channel_adapters.whatsapp_adapter import WhatsAppChannelAdapter
from app.contracts.channel_adapter import ChannelAdapter
from app.contracts.decision_router import DecisionRouter
from app.contracts.knowledge_provider import KnowledgeProvider
from app.contracts.logging_service import LoggingService
from app.contracts.manager_queue_repository import ManagerQueueRepository
from app.core.config import get_settings
from app.core.constants import ChannelType
from app.knowledge_layer.knowledge_base_provider import KnowledgeBaseProvider
from app.knowledge_layer.source_selector import SourceSelector
from app.prompt_builder import DefaultPromptBuilder
from app.repositories.conversations import SqlAlchemyConversationRepository
from app.repositories.manager_queue import SqlAlchemyManagerQueueRepository
from app.repositories.sessions import SqlAlchemySessionRepository
from app.services.conversation_state_service import ConversationStateService
from app.services.decision_router import DefaultDecisionRouter
from app.services.handoff_manager import DefaultHandoffManager
from app.services.logging_service import SqlAlchemyLoggingService
from app.services.message_pipeline import MessagePipelineService
from app.services.response_sender import ChannelResponseSender, InMemoryResponseSender


# Process-local MVP stores shared across default composition.
_SESSION_REPOSITORY = SqlAlchemySessionRepository()
_CONVERSATION_REPOSITORY = SqlAlchemyConversationRepository()
_MANAGER_QUEUE_REPOSITORY: ManagerQueueRepository = SqlAlchemyManagerQueueRepository()
_LOGGING_SERVICE: LoggingService = SqlAlchemyLoggingService()
_IN_MEMORY_SENDER = InMemoryResponseSender()
_MAX_ADAPTER = MaxChannelAdapter()
_EMAIL_ADAPTER = EmailChannelAdapter()
_WHATSAPP_ADAPTER = WhatsAppChannelAdapter()
_WEBSITE_FORM_ADAPTER = WebsiteFormAdapter()
_WEBSITE_CHAT_ADAPTER = WebsiteChatAdapter()


def build_conversation_state() -> ConversationStateService:
    return ConversationStateService(
        session_repository=_SESSION_REPOSITORY,
        conversation_repository=_CONVERSATION_REPOSITORY,
    )


def build_source_selector(providers: list[KnowledgeProvider] | None = None) -> SourceSelector:
    return SourceSelector(providers=providers or [KnowledgeBaseProvider.from_items([])])


def build_message_pipeline(
    providers: list[KnowledgeProvider] | None = None,
    llm_provider=None,
) -> MessagePipelineService:
    settings = get_settings()
    return MessagePipelineService(
        conversation_state=build_conversation_state(),
        source_selector=build_source_selector(providers),
        prompt_builder=DefaultPromptBuilder(),
        ai_core=AICore(
            llm_provider=llm_provider
            or OpenAIProvider(settings.openai_api_key, settings.openai_model),
            validator=AIValidator(),
        ),
        logging_service=_LOGGING_SERVICE,
    )


def default_channel_adapters() -> dict[ChannelType, ChannelAdapter]:
    return {
        ChannelType.MAX: _MAX_ADAPTER,
        ChannelType.EMAIL: _EMAIL_ADAPTER,
        ChannelType.WHATSAPP: _WHATSAPP_ADAPTER,
        ChannelType.WEBSITE_FORM: _WEBSITE_FORM_ADAPTER,
        ChannelType.WEBSITE_CHAT: _WEBSITE_CHAT_ADAPTER,
    }


def build_decision_router(
    channel_adapters: dict[ChannelType, ChannelAdapter] | None = None,
) -> DecisionRouter:
    return DefaultDecisionRouter(
        response_sender=ChannelResponseSender(
            adapters=channel_adapters if channel_adapters is not None else default_channel_adapters(),
            fallback=_IN_MEMORY_SENDER,
        ),
        handoff_manager=DefaultHandoffManager(_MANAGER_QUEUE_REPOSITORY),
        logging_service=_LOGGING_SERVICE,
    )


def get_manager_queue_repository() -> ManagerQueueRepository:
    return _MANAGER_QUEUE_REPOSITORY


def get_logging_service() -> LoggingService:
    return _LOGGING_SERVICE


def get_max_adapter() -> MaxChannelAdapter:
    return _MAX_ADAPTER


def get_email_adapter() -> EmailChannelAdapter:
    return _EMAIL_ADAPTER


def get_whatsapp_adapter() -> WhatsAppChannelAdapter:
    return _WHATSAPP_ADAPTER


def get_website_form_adapter() -> WebsiteFormAdapter:
    return _WEBSITE_FORM_ADAPTER


def get_website_chat_adapter() -> WebsiteChatAdapter:
    return _WEBSITE_CHAT_ADAPTER
