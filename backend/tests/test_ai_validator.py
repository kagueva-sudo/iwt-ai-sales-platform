from app.ai_core.validator import AIValidator
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse
from app.domain.products import Product, ProductSearchResult


def test_validator_approves_response_with_confirmed_sources() -> None:
    validator = AIValidator()
    product_data = ProductSearchResult(
        query="насос",
        products=[Product(sku="P-1", name="Насос", source="1c")],
        source="1c",
    )
    ai_response = AIResponse(text="Подтвержденный ответ.", sources=["1c"])

    result = validator.validate(ai_response, product_data)

    assert result.status == AIValidationStatus.APPROVED
    assert result.approved_text == "Подтвержденный ответ."


def test_validator_requires_data_when_product_data_is_missing() -> None:
    validator = AIValidator()
    product_data = ProductSearchResult(query="насос", products=[], source="mock")
    ai_response = AIResponse(text="Цена 1000 рублей.", sources=["ai"])

    result = validator.validate(ai_response, product_data)

    assert result.status == AIValidationStatus.NEEDS_DATA
    assert "уточнить" in (result.approved_text or "")


def test_validator_requires_data_without_sources() -> None:
    validator = AIValidator()
    product_data = ProductSearchResult(
        query="насос",
        products=[Product(sku="P-1", name="Насос", source="1c")],
        source="1c",
    )
    ai_response = AIResponse(text="Ответ без источника.")

    result = validator.validate(ai_response, product_data)

    assert result.status == AIValidationStatus.NEEDS_DATA


def test_validator_blocks_price_without_confirmed_price() -> None:
    validator = AIValidator()
    product_data = ProductSearchResult(
        query="насос",
        products=[Product(sku="P-1", name="Насос", source="1c")],
        source="1c",
    )
    ai_response = AIResponse(text="Цена насоса 1000 рублей.", sources=["1c"])

    result = validator.validate(ai_response, product_data)

    assert result.status == AIValidationStatus.NEEDS_DATA
    assert "price" in (result.reason or "")


def test_validator_approves_price_with_confirmed_price() -> None:
    validator = AIValidator()
    product_data = ProductSearchResult(
        query="насос",
        products=[Product(sku="P-1", name="Насос", price=1000, source="1c")],
        source="1c",
    )
    ai_response = AIResponse(text="Цена насоса 1000 рублей.", sources=["1c"])

    result = validator.validate(ai_response, product_data)

    assert result.status == AIValidationStatus.APPROVED
