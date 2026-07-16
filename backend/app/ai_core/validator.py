from app.ai_core.prompts import SAFE_HANDOFF_MESSAGE
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse, ValidationResult
from app.domain.products import ProductSearchResult


COMMERCIAL_FACT_CHECKS = {
    "price": "has_confirmed_price",
    "stock": "has_confirmed_stock",
    "characteristics": "has_confirmed_characteristics",
    "delivery_terms": "has_confirmed_delivery_terms",
}


class AIValidator:
    def validate(self, ai_response: AIResponse, product_data: ProductSearchResult | None) -> ValidationResult:
        if ai_response.needs_handoff:
            return ValidationResult(
                status=AIValidationStatus.HANDOFF_REQUIRED,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason="AI requested manager handoff.",
                sources=ai_response.sources,
            )

        if product_data is not None and not product_data.has_confirmed_data:
            return ValidationResult(
                status=AIValidationStatus.NEEDS_DATA,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason="No confirmed product data available.",
                sources=[product_data.source],
            )

        missing_facts = self._find_missing_commercial_facts(ai_response, product_data)
        if missing_facts:
            return ValidationResult(
                status=AIValidationStatus.NEEDS_DATA,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason=f"Missing confirmed commercial facts: {', '.join(sorted(missing_facts))}.",
                sources=[product_data.source] if product_data else [],
            )

        if not ai_response.sources:
            return ValidationResult(
                status=AIValidationStatus.NEEDS_DATA,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason="AI response has no confirmed sources.",
            )

        return ValidationResult(
            status=AIValidationStatus.APPROVED,
            approved_text=ai_response.text,
            sources=ai_response.sources,
        )

    def _find_missing_commercial_facts(
        self,
        ai_response: AIResponse,
        product_data: ProductSearchResult | None,
    ) -> set[str]:
        requested_facts = self._detect_commercial_facts(ai_response.text) | ai_response.requested_facts
        if not requested_facts:
            return set()

        if product_data is None or not product_data.has_confirmed_data:
            return requested_facts

        missing_facts: set[str] = set()
        for fact in requested_facts:
            check_name = COMMERCIAL_FACT_CHECKS.get(fact)
            if check_name and not getattr(product_data, check_name):
                missing_facts.add(fact)
        return missing_facts

    def _detect_commercial_facts(self, text: str) -> set[str]:
        lowered = text.lower()
        fact_keywords = {
            "price": ("цена", "стоимость", "руб", "₽", "р."),
            "stock": ("налич", "остат", "склад"),
            "characteristics": ("характерист", "мощность", "размер", "габарит", "описание"),
            "delivery_terms": ("срок", "поставка", "доставка", "когда будет"),
        }
        return {
            fact
            for fact, keywords in fact_keywords.items()
            if any(keyword in lowered for keyword in keywords)
        }
