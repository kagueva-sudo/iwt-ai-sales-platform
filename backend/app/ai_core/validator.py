from app.ai_core.prompts import SAFE_HANDOFF_MESSAGE
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse, ValidationResult
from app.domain.products import ProductSearchResult


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
