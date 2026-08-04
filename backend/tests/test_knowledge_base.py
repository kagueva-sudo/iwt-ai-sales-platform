import pytest

from app.domain.knowledge import KnowledgeItem
from app.knowledge_layer.knowledge_base_provider import KnowledgeBaseProvider
from app.knowledge_layer.search_service import KnowledgeSearchService
from app.knowledge_layer.source_selector import SourceSelector
from app.repositories.knowledge import InMemoryKnowledgeRepository


pytestmark = pytest.mark.asyncio


def _sample_items() -> list[KnowledgeItem]:
    return [
        KnowledgeItem(
            id="faq-delivery",
            title="Доставка",
            content="Доставка занимает 2 дня по Москве.",
            category="faq",
            item_type="faq",
            tags=["доставка", "сроки"],
        ),
        KnowledgeItem(
            id="rule-payment",
            title="Оплата",
            content="Оплата возможна по счёту и картой.",
            category="rules",
            item_type="rule",
            tags=["оплата"],
        ),
    ]


async def test_knowledge_repository_stores_items_with_confirmed_fields() -> None:
    repository = InMemoryKnowledgeRepository()

    stored = await repository.add(
        KnowledgeItem(id="faq-1", title="Гарантия", content="Гарантия 12 месяцев.", category="faq")
    )

    assert stored.confirmed_fields
    assert "content" in stored.confirmed_fields
    assert await repository.get_by_id("faq-1") is not None


async def test_knowledge_search_service_finds_by_title_and_tags() -> None:
    service = KnowledgeSearchService(InMemoryKnowledgeRepository(_sample_items()))

    by_title = await service.search("доставка")
    by_tag = await service.search("оплата")
    missing = await service.search("несуществующий запрос")

    assert len(by_title) == 1
    assert by_title[0].id == "faq-delivery"
    assert len(by_tag) == 1
    assert by_tag[0].id == "rule-payment"
    assert missing == []


async def test_knowledge_base_provider_returns_verified_sources() -> None:
    provider = KnowledgeBaseProvider.from_items(_sample_items())

    result = await provider.search("доставка")

    assert result.has_sources
    assert result.sources[0].source_type == "knowledge_base"
    assert "content" in result.sources[0].metadata["confirmed_fields"]


async def test_knowledge_base_empty_query_returns_no_sources() -> None:
    provider = KnowledgeBaseProvider.from_items(_sample_items())

    result = await provider.search("   ")

    assert result.has_sources is False


async def test_source_selector_uses_knowledge_provider_contract() -> None:
    provider = KnowledgeBaseProvider.from_items(_sample_items())
    selector = SourceSelector([provider])

    result = await selector.select_sources("оплата")

    assert [source.source_id for source in result.sources] == ["rule-payment"]


async def test_knowledge_search_is_case_insensitive() -> None:
    service = KnowledgeSearchService(InMemoryKnowledgeRepository(_sample_items()))

    result = await service.search("ДОСТАВКА")

    assert [item.id for item in result] == ["faq-delivery"]


async def test_knowledge_search_supports_multi_word_query() -> None:
    service = KnowledgeSearchService(InMemoryKnowledgeRepository(_sample_items()))

    result = await service.search("доставка москве")

    assert [item.id for item in result] == ["faq-delivery"]


async def test_knowledge_search_ranks_by_match_count() -> None:
    items = [
        KnowledgeItem(
            id="weak-match",
            title="Общая информация",
            content="У нас есть насосы.",
            category="general",
            tags=["каталог"],
        ),
        KnowledgeItem(
            id="strong-match",
            title="Насос промышленный",
            content="Насос для промышленности. Насос доступен на складе.",
            category="products",
            tags=["насос", "склад"],
        ),
        KnowledgeItem(
            id="medium-match",
            title="Каталог",
            content="Насос указан в прайсе.",
            category="products",
            tags=["насос"],
        ),
    ]
    service = KnowledgeSearchService(InMemoryKnowledgeRepository(items))

    result = await service.search("насос склад")

    assert [item.id for item in result] == ["strong-match", "medium-match", "weak-match"]


async def test_knowledge_search_matches_category() -> None:
    service = KnowledgeSearchService(
        InMemoryKnowledgeRepository(
            [
                KnowledgeItem(
                    id="delivery-1",
                    title="Сроки",
                    content="Отгрузка со склада.",
                    category="delivery",
                    tags=[],
                )
            ]
        )
    )

    result = await service.search("delivery")

    assert [item.id for item in result] == ["delivery-1"]
