"""Regression suite: free-text intelligence for MAX/IWT dialogs (Architecture Freeze)."""

import pytest

from app.ai_core.commercial_facts import detect_requested_commercial_facts
from app.ai_core.core import AICore
from app.ai_core.llm_provider import LLMProvider
from app.ai_core.prompts import (
    CARTRIDGE_CLARIFY_MESSAGE,
    GREETING_MESSAGE,
    SAFE_HANDOFF_MESSAGE,
    THANKS_MESSAGE,
)
from app.ai_core.validator import AIValidator
from app.contracts.knowledge_provider import KnowledgeProvider
from app.core.constants import ChannelType, HandoffReason, MessageDirection
from app.domain.conversations import ConversationMessage
from app.domain.messages import Message
from app.domain.processing import ProcessingDecision
from app.domain.prompt_context import PromptContext
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.knowledge_layer.source_selector import SourceSelector
from app.prompt_builder import DefaultPromptBuilder
from app.repositories.conversations import InMemoryConversationRepository
from app.repositories.sessions import InMemorySessionRepository
from app.services.conversation_state_service import ConversationStateService
from app.services.message_pipeline import MessagePipelineService


pytestmark = pytest.mark.asyncio


class StubLLMProvider(LLMProvider):
    def __init__(self, text: str = "Ответ из LLM.") -> None:
        self.text = text
        self.last_user_message = ""

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        self.last_user_message = user_message
        assert "Verified sources" in system_prompt
        return self.text


class StubKnowledgeProvider(KnowledgeProvider):
    def __init__(self, sources: list[VerifiedSource] | None = None) -> None:
        self._sources = sources or []
        self.last_query = ""

    async def search(self, query: str) -> SourceSelectionResult:
        self.last_query = query
        return SourceSelectionResult(query=query, sources=list(self._sources))


def _build_pipeline(
    llm: LLMProvider | None = None,
    sources: list[VerifiedSource] | None = None,
    provider: StubKnowledgeProvider | None = None,
) -> tuple[MessagePipelineService, StubKnowledgeProvider]:
    provider = provider or StubKnowledgeProvider(sources)
    conversation_state = ConversationStateService(
        session_repository=InMemorySessionRepository(),
        conversation_repository=InMemoryConversationRepository(),
    )
    pipeline = MessagePipelineService(
        conversation_state=conversation_state,
        source_selector=SourceSelector([provider]),
        prompt_builder=DefaultPromptBuilder(),
        ai_core=AICore(llm or StubLLMProvider(), AIValidator()),
    )
    return pipeline, provider


@pytest.mark.parametrize(
    "text",
    [
        "Привет",
        "привет!",
        "Добрый день",
        "Добрый день!",
        "Здравствуйте.",
        "Здравствуйте!",
        "hello!",
        "Привет😊",
    ],
)
async def test_greetings_do_not_fallback_or_handoff(text: str) -> None:
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(text=text, channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == GREETING_MESSAGE
    assert result.metadata.get("intent") == "greeting"
    assert result.handoff_reason is None


async def test_thanks_gets_natural_reply() -> None:
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(text="Спасибо", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == THANKS_MESSAGE


async def test_cartridges_query_clarifies_instead_of_payment_handoff() -> None:
    assert "payment_terms" not in detect_requested_commercial_facts("У вас есть картриджи в продаже?")
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(
            text="У вас есть картриджи в продаже?",
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id="u1",
        )
    )
    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == CARTRIDGE_CLARIFY_MESSAGE
    assert result.metadata.get("intent") in {"product_search", "availability_question", "price_question"}
    assert result.handoff_reason is None


async def test_needed_cartridge_asks_for_printer_model() -> None:
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(text="Мне нужен картридж", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert result.decision == ProcessingDecision.RESPOND
    assert "принтер" in (result.response_text or "").lower() or "модель" in (result.response_text or "").lower()
    assert result.metadata.get("intent") == "product_search"


async def test_followup_model_keeps_cartridge_context_in_search() -> None:
    provider = StubKnowledgeProvider([])
    pipeline, provider = _build_pipeline(provider=provider)
    first = await pipeline.process(
        Message(text="Мне нужен картридж", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert first.decision == ProcessingDecision.RESPOND

    second = await pipeline.process(
        Message(text="HP LaserJet M404", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert "картридж" in provider.last_query.lower()
    assert "m404" in provider.last_query.lower() or "LaserJet" in provider.last_query
    assert second.metadata.get("intent") in {"product_search", "unknown", "availability_question"}


async def test_manager_request_goes_to_handoff() -> None:
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(
            text="Соедините меня с менеджером",
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id="u1",
        )
    )
    assert result.decision == ProcessingDecision.HANDOFF
    assert result.handoff_reason == HandoffReason.CLIENT_REQUEST_MANAGER
    assert result.metadata.get("intent") == "manager_request"


async def test_delivery_question_uses_kb_without_handoff() -> None:
    source = VerifiedSource(
        source_id="delivery-1",
        source_type="knowledge_base",
        title="Доставка",
        content="Доставка по РФ курьером и транспортными компаниями.",
        metadata={"confirmed_fields": "content,delivery_terms"},
    )
    llm = StubLLMProvider("Доставка по РФ курьером и транспортными компаниями.")
    pipeline, _ = _build_pipeline(llm=llm, sources=[source])
    result = await pipeline.process(
        Message(
            text="Как осуществляется доставка?",
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id="u1",
        )
    )
    assert result.decision == ProcessingDecision.RESPOND
    assert "доставк" in (result.response_text or "").lower()
    assert result.handoff_reason is None


async def test_payment_question_uses_kb() -> None:
    source = VerifiedSource(
        source_id="payment-1",
        source_type="knowledge_base",
        title="Оплата",
        content="Оплата картой, наличными и безналом для юрлиц.",
        metadata={"confirmed_fields": "content,payment_terms"},
    )
    llm = StubLLMProvider("Оплата картой, наличными и безналом для юрлиц.")
    pipeline, _ = _build_pipeline(llm=llm, sources=[source])
    result = await pipeline.process(
        Message(
            text="Какие способы оплаты?",
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id="u1",
        )
    )
    assert result.decision == ProcessingDecision.RESPOND
    assert "оплат" in (result.response_text or "").lower()


async def test_vague_followup_uses_history_not_blind_menu() -> None:
    core = AICore(StubLLMProvider(), AIValidator())
    ctx = PromptContext(
        system_prompt="sys",
        user_message="Мне нужен подходящий вариант",
        recent_messages=[
            ConversationMessage(role="user", text="Мне нужен картридж"),
            ConversationMessage(role="assistant", text=CARTRIDGE_CLARIFY_MESSAGE),
        ],
    )
    result = await core.process(ctx)
    assert result.decision == ProcessingDecision.RESPOND
    assert result.metadata.get("intent") == "product_search"
    assert result.response_text == CARTRIDGE_CLARIFY_MESSAGE


async def test_llm_receives_dialog_history() -> None:
    source = VerifiedSource(
        source_id="p1",
        source_type="catalog",
        title="Картридж HP",
        content="Картридж для HP LaserJet M404",
        metadata={"confirmed_fields": "description"},
    )
    llm = StubLLMProvider("Могу предложить картридж для HP LaserJet M404.")
    pipeline, _ = _build_pipeline(llm=llm, sources=[source])
    await pipeline.process(
        Message(text="Мне нужен картридж", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    await pipeline.process(
        Message(text="HP LaserJet M404", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert "История диалога" in llm.last_user_message or "Recent conversation" in llm.last_user_message or "картридж" in llm.last_user_message.lower()


async def test_empty_message_is_unknown_or_ignored_safely() -> None:
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(text="   ", channel=ChannelType.MAX, direction=MessageDirection.INBOUND, customer_id="u1")
    )
    assert result.decision in {ProcessingDecision.NEEDS_MORE_DATA, ProcessingDecision.HANDOFF, ProcessingDecision.RESPOND}


async def test_consultation_when_user_cannot_choose() -> None:
    pipeline, _ = _build_pipeline()
    result = await pipeline.process(
        Message(
            text="Не знаю, что выбрать",
            channel=ChannelType.MAX,
            direction=MessageDirection.INBOUND,
            customer_id="u1",
        )
    )
    assert result.metadata.get("intent") == "consultation"
    assert result.decision in {ProcessingDecision.NEEDS_MORE_DATA, ProcessingDecision.RESPOND, ProcessingDecision.HANDOFF}


async def test_payment_card_not_confused_with_cartridge() -> None:
    assert "payment_terms" not in detect_requested_commercial_facts("нужны картриджи")
    assert "payment_terms" in detect_requested_commercial_facts("можно оплатить картой")
    assert "payment_terms" in detect_requested_commercial_facts("оплата по карте")
