import pytest
from fastapi.testclient import TestClient

from app.ai_core.core import AICore
from app.ai_core.llm_provider import LLMProvider
from app.ai_core.validator import AIValidator
from app.channel_adapters.website_chat_adapter import WebsiteChatAdapter
from app.channel_adapters.website_form_adapter import WebsiteFormAdapter
from app.contracts.knowledge_provider import KnowledgeProvider
from app.core.constants import ChannelType, MessageDirection
from app.core.errors import ProviderError
from app.domain.processing import ProcessingDecision
from app.domain.sources import SourceSelectionResult, VerifiedSource
from app.knowledge_layer.source_selector import SourceSelector
from app.main import app
from app.prompt_builder import DefaultPromptBuilder
from app.repositories.conversations import InMemoryConversationRepository
from app.repositories.sessions import InMemorySessionRepository
from app.services.conversation_state_service import ConversationStateService
from app.services.message_pipeline import MessagePipelineService


class StubLLMProvider(LLMProvider):
    def __init__(self, text: str = "Цена насоса 1000 рублей.") -> None:
        self.text = text

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        return self.text


class StubKnowledgeProvider(KnowledgeProvider):
    def __init__(self, sources: list[VerifiedSource] | None = None) -> None:
        self._sources = sources or []

    async def search(self, query: str) -> SourceSelectionResult:
        return SourceSelectionResult(query=query, sources=list(self._sources))


def _confirmed_price_source() -> VerifiedSource:
    return VerifiedSource(
        source_id="P-1",
        source_type="knowledge_base",
        title="Насос",
        content="Насос промышленный",
        metadata={"confirmed_fields": "name,price,sku"},
    )


def _build_pipeline(sources: list[VerifiedSource] | None = None) -> MessagePipelineService:
    return MessagePipelineService(
        conversation_state=ConversationStateService(
            session_repository=InMemorySessionRepository(),
            conversation_repository=InMemoryConversationRepository(),
        ),
        source_selector=SourceSelector(providers=[StubKnowledgeProvider(sources)]),
        prompt_builder=DefaultPromptBuilder(),
        ai_core=AICore(llm_provider=StubLLMProvider(), validator=AIValidator()),
    )


@pytest.mark.asyncio
async def test_website_form_adapter_normalizes_payload() -> None:
    adapter = WebsiteFormAdapter()

    message = await adapter.normalize_incoming(
        {
            "message": "Нужна цена насоса",
            "email": "client@example.com",
            "name": "Иван",
            "form_id": "contact-form",
        }
    )

    assert message.channel == ChannelType.WEBSITE_FORM
    assert message.direction == MessageDirection.INBOUND
    assert message.text == "Нужна цена насоса"
    assert message.customer_id == "contact-form"
    assert message.customer_contact == "client@example.com"


@pytest.mark.asyncio
async def test_website_chat_adapter_normalizes_payload() -> None:
    adapter = WebsiteChatAdapter()

    message = await adapter.normalize_incoming(
        {
            "text": "Нужна цена насоса",
            "visitor_id": "visitor-1",
            "contact": "+79990001122",
        }
    )

    assert message.channel == ChannelType.WEBSITE_CHAT
    assert message.text == "Нужна цена насоса"
    assert message.customer_id == "visitor-1"
    assert message.customer_contact == "+79990001122"


@pytest.mark.asyncio
async def test_website_adapters_reject_empty_payload() -> None:
    with pytest.raises(ProviderError):
        await WebsiteFormAdapter().normalize_incoming({"email": "a@b.c"})
    with pytest.raises(ProviderError):
        await WebsiteChatAdapter().normalize_incoming({"visitor_id": "1"})


def test_website_form_webhook_handoff() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/channels/website/form",
            json={
                "message": "Какая мощность насоса?",
                "email": "client@example.com",
                "form_id": "form-1",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["handoff_required"] is True
    assert body["validation_status"] == "handoff_required"


def test_website_chat_webhook_handoff() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/channels/website/chat",
            json={
                "text": "Какая мощность насоса?",
                "visitor_id": "v-1",
                "contact": "+79991112233",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["handoff_required"] is True
    assert body["validation_status"] == "handoff_required"


@pytest.mark.asyncio
async def test_website_form_and_chat_use_same_pipeline() -> None:
    pipeline = _build_pipeline(sources=[_confirmed_price_source()])
    form_message = await WebsiteFormAdapter().normalize_incoming(
        {"message": "Какая цена насоса?", "email": "a@b.c", "form_id": "f-1"}
    )
    chat_message = await WebsiteChatAdapter().normalize_incoming(
        {"text": "Какая цена насоса?", "visitor_id": "v-1", "contact": "a@b.c"}
    )

    form_result = await pipeline.process(form_message)
    chat_result = await pipeline.process(chat_message)

    assert form_result.decision == chat_result.decision == ProcessingDecision.RESPOND
    assert form_result.response_text == chat_result.response_text
    assert form_message.channel == ChannelType.WEBSITE_FORM
    assert chat_message.channel == ChannelType.WEBSITE_CHAT


@pytest.mark.asyncio
async def test_website_channels_approved_response() -> None:
    pipeline = _build_pipeline(sources=[_confirmed_price_source()])
    message = await WebsiteFormAdapter().normalize_incoming(
        {"message": "Какая цена насоса?", "email": "a@b.c", "form_id": "f-2"}
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == "Цена насоса 1000 рублей."
    assert "P-1" in result.sources


@pytest.mark.asyncio
async def test_website_channels_price_guidance_without_sources() -> None:
    from app.ai_core.prompts import STOCK_PRICE_GUIDANCE_MESSAGE

    pipeline = _build_pipeline(sources=[])
    message = await WebsiteChatAdapter().normalize_incoming(
        {"text": "Какая цена насоса?", "visitor_id": "v-2"}
    )

    result = await pipeline.process(message)

    assert result.decision == ProcessingDecision.RESPOND
    assert result.response_text == STOCK_PRICE_GUIDANCE_MESSAGE


def test_ai_core_does_not_know_website_channels() -> None:
    import app.ai_core.core as core_module
    import app.api.website as website_api

    core_source = open(core_module.__file__, encoding="utf-8").read()
    api_source = open(website_api.__file__, encoding="utf-8").read()

    assert "WebsiteFormAdapter" not in core_source
    assert "WebsiteChatAdapter" not in core_source
    assert "channel_adapters" not in core_source
    assert "AICore" not in api_source
    assert "ai_core" not in api_source


def test_website_api_rejects_invalid_payload() -> None:
    with TestClient(app) as client:
        form_response = client.post("/channels/website/form", json={"email": "a@b.c"})
        chat_response = client.post("/channels/website/chat", json={"visitor_id": "1"})

    assert form_response.status_code == 400
    assert chat_response.status_code == 400
