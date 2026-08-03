from app.ai_core.source_mapping import products_to_verified_sources
from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse
from app.domain.products import Product, ProductSearchResult
from app.domain.sources import VerifiedSource


def test_validator_approves_response_with_confirmed_sources() -> None:
    validator = AIValidator()
    sources = [
        VerifiedSource(
            source_id="P-1",
            source_type="1c",
            title="Насос",
            content="Насос",
            metadata={"confirmed_fields": "sku,name"},
        )
    ]
    ai_response = AIResponse(text="Подтвержденный ответ.", sources=["P-1"])

    result = validator.validate(ai_response, sources)

    assert result.status == AIValidationStatus.APPROVED
    assert result.approved_text == "Подтвержденный ответ."


def test_validator_requires_data_when_verified_sources_are_missing() -> None:
    validator = AIValidator()
    ai_response = AIResponse(text="Цена 1000 рублей.", sources=["ai"])

    result = validator.validate(ai_response, [])

    assert result.status == AIValidationStatus.NEEDS_DATA
    assert "уточнить" in (result.approved_text or "")


def test_validator_requires_data_without_sources() -> None:
    validator = AIValidator()
    sources = [
        VerifiedSource(
            source_id="P-1",
            source_type="1c",
            title="Насос",
            content="Насос",
            metadata={"confirmed_fields": "sku,name"},
        )
    ]
    ai_response = AIResponse(text="Ответ без источника.")

    result = validator.validate(ai_response, sources)

    assert result.status == AIValidationStatus.NEEDS_DATA


def test_validator_blocks_price_without_confirmed_price() -> None:
    validator = AIValidator()
    sources = [
        VerifiedSource(
            source_id="P-1",
            source_type="1c",
            title="Насос",
            content="Насос",
            metadata={"confirmed_fields": "sku,name"},
        )
    ]
    ai_response = AIResponse(text="Цена насоса 1000 рублей.", sources=["P-1"])

    result = validator.validate(ai_response, sources)

    assert result.status == AIValidationStatus.NEEDS_DATA
    assert "price" in (result.reason or "")


def test_validator_approves_price_with_confirmed_price() -> None:
    validator = AIValidator()
    sources = [
        VerifiedSource(
            source_id="P-1",
            source_type="1c",
            title="Насос",
            content="Насос",
            metadata={"confirmed_fields": "sku,name,price"},
        )
    ]
    ai_response = AIResponse(text="Цена насоса 1000 рублей.", sources=["P-1"])

    result = validator.validate(ai_response, sources)

    assert result.status == AIValidationStatus.APPROVED


def test_validator_blocks_price_when_field_is_not_confirmed() -> None:
    validator = AIValidator()
    product_data = ProductSearchResult(
        query="насос",
        products=[
            Product(
                sku="P-1",
                name="Насос",
                price=1000,
                source="website",
                confirmed_fields={"sku", "name"},
            )
        ],
        source="website",
    )
    ai_response = AIResponse(text="Цена насоса 1000 рублей.", sources=["P-1"])

    result = validator.validate(ai_response, products_to_verified_sources(product_data))

    assert result.status == AIValidationStatus.NEEDS_DATA
    assert "price" in (result.reason or "")
