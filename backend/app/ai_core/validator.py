from app.ai_core.prompts import SAFE_HANDOFF_MESSAGE
from app.core.constants import AIValidationStatus
from app.domain.ai import AIResponse, ValidationResult
from app.domain.sources import VerifiedSource


FACT_TO_CONFIRMED_FIELDS: dict[str, set[str]] = {
    "price": {"price"},
    "stock": {"stock_qty", "availability_status"},
    "characteristics": {"characteristics", "description"},
    "delivery_terms": {"delivery_terms"},
}


class AIValidator:
    """Validates a finished AIResponse against already selected VerifiedSources."""

    def validate(
        self,
        ai_response: AIResponse,
        verified_sources: list[VerifiedSource],
    ) -> ValidationResult:
        if ai_response.needs_handoff:
            return ValidationResult(
                status=AIValidationStatus.HANDOFF_REQUIRED,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason="AI requested manager handoff.",
                sources=ai_response.sources,
            )

        if not verified_sources:
            return ValidationResult(
                status=AIValidationStatus.NEEDS_DATA,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason="No confirmed verified sources available.",
            )

        missing_facts = self._find_missing_commercial_facts(ai_response, verified_sources)
        if missing_facts:
            return ValidationResult(
                status=AIValidationStatus.NEEDS_DATA,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason=f"Missing confirmed commercial facts: {', '.join(sorted(missing_facts))}.",
                sources=self._source_ids(verified_sources),
            )

        if not ai_response.sources:
            return ValidationResult(
                status=AIValidationStatus.NEEDS_DATA,
                approved_text=SAFE_HANDOFF_MESSAGE,
                reason="AI response has no confirmed sources.",
                sources=self._source_ids(verified_sources),
            )

        return ValidationResult(
            status=AIValidationStatus.APPROVED,
            approved_text=ai_response.text,
            sources=ai_response.sources,
        )

    def _find_missing_commercial_facts(
        self,
        ai_response: AIResponse,
        verified_sources: list[VerifiedSource],
    ) -> set[str]:
        requested_facts = self._detect_commercial_facts(ai_response.text) | ai_response.requested_facts
        if not requested_facts:
            return set()

        missing_facts: set[str] = set()
        for fact in requested_facts:
            if not self._sources_confirm_fact(verified_sources, fact):
                missing_facts.add(fact)
        return missing_facts

    def _sources_confirm_fact(self, verified_sources: list[VerifiedSource], fact: str) -> bool:
        needed_fields = FACT_TO_CONFIRMED_FIELDS.get(fact, {fact})
        for source in verified_sources:
            confirmed_fields = self._parse_confirmed_fields(source)
            if confirmed_fields & needed_fields:
                return True
        return False

    def _parse_confirmed_fields(self, source: VerifiedSource) -> set[str]:
        raw = source.metadata.get("confirmed_fields", "")
        if not raw.strip():
            return set()
        return {part.strip() for part in raw.split(",") if part.strip()}

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

    def _source_ids(self, verified_sources: list[VerifiedSource]) -> list[str]:
        return [source.source_id for source in verified_sources]
