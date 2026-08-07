from app.ai_core.llm_provider import LLMProvider
from app.ai_core.prompts import GREETING_MESSAGE, SAFE_HANDOFF_MESSAGE
from app.ai_core.validator import FACT_TO_CONFIRMED_FIELDS, AIValidator
from app.core.constants import AIValidationStatus, HandoffReason
from app.core.errors import ProviderError
from app.domain.ai import AIResponse
from app.domain.processing import ProcessingDecision, ProcessingResult
from app.domain.prompt_context import PromptContext
from app.domain.sources import VerifiedSource


_GREETING_PHRASES = (
    "/start",
    "start",
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "доброго дня",
    "hello",
    "hi",
)


class AICore:
    """AI Core v2: consumes PromptContext, calls LLM + Validator, returns ProcessingResult.

    Does not call providers, repositories, gateway, channels, handoff, or decision router.
    """

    def __init__(self, llm_provider: LLMProvider, validator: AIValidator) -> None:
        self.llm_provider = llm_provider
        self.validator = validator

    async def process(self, prompt_context: PromptContext) -> ProcessingResult:
        source_ids = [source.source_id for source in prompt_context.verified_sources]
        requested_facts = self._detect_requested_commercial_facts(prompt_context.user_message)

        if not prompt_context.verified_sources:
            if self._is_conversational_open(prompt_context.user_message) and not requested_facts:
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=GREETING_MESSAGE,
                    sources=[],
                    metadata={"reason": "conversational_greeting"},
                )
            return ProcessingResult(
                decision=ProcessingDecision.HANDOFF,
                response_text=SAFE_HANDOFF_MESSAGE,
                handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
                sources=[],
                metadata={"reason": "no_verified_sources"},
            )

        try:
            draft = await self.llm_provider.generate_response(
                prompt_context.system_prompt,
                prompt_context.user_message,
            )
            ai_response = AIResponse(
                text=draft,
                sources=source_ids,
                requested_facts=requested_facts,
            )
        except ProviderError as exc:
            if self._sources_cover_facts(prompt_context.verified_sources, requested_facts):
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=self._format_kb_answer(
                        prompt_context.verified_sources,
                        prompt_context.user_message,
                    ),
                    sources=source_ids,
                    errors=[str(exc)],
                    metadata={"reason": "llm_fallback_kb"},
                )
            return ProcessingResult(
                decision=ProcessingDecision.ERROR,
                response_text=SAFE_HANDOFF_MESSAGE,
                handoff_reason=HandoffReason.LLM_ERROR,
                sources=source_ids,
                errors=[str(exc)],
            )

        validation = self.validator.validate(ai_response, prompt_context.verified_sources)
        result = self._to_processing_result(ai_response, validation)
        if (
            result.decision != ProcessingDecision.RESPOND
            and self._sources_cover_facts(prompt_context.verified_sources, requested_facts)
        ):
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=self._format_kb_answer(
                    prompt_context.verified_sources,
                    prompt_context.user_message,
                ),
                sources=source_ids,
                metadata={
                    "reason": "validator_fallback_kb",
                    "validation_reason": result.metadata.get("reason", validation.reason or ""),
                },
            )
        return result

    def _to_processing_result(self, ai_response: AIResponse, validation) -> ProcessingResult:
        if validation.status == AIValidationStatus.APPROVED:
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=validation.approved_text or ai_response.text,
                sources=validation.sources or ai_response.sources,
            )

        if validation.status == AIValidationStatus.NEEDS_DATA:
            return ProcessingResult(
                decision=ProcessingDecision.NEEDS_MORE_DATA,
                response_text=validation.approved_text or SAFE_HANDOFF_MESSAGE,
                handoff_reason=ai_response.handoff_reason or HandoffReason.NO_CONFIRMED_DATA,
                sources=validation.sources or ai_response.sources,
                metadata={"reason": validation.reason or "needs_more_data"},
            )

        return ProcessingResult(
            decision=ProcessingDecision.HANDOFF,
            response_text=validation.approved_text or SAFE_HANDOFF_MESSAGE,
            handoff_reason=ai_response.handoff_reason or HandoffReason.NO_CONFIRMED_DATA,
            sources=validation.sources or ai_response.sources,
            metadata={"reason": validation.reason or "handoff_required"},
        )

    def _detect_requested_commercial_facts(self, text: str) -> set[str]:
        lowered = text.lower()
        fact_keywords = {
            "price": ("цена", "стоимость", "сколько стоит", "прайс"),
            "stock": ("налич", "остат", "на складе"),
            "characteristics": ("характерист", "параметр", "мощность", "размер", "габарит"),
            "delivery_terms": ("срок", "поставка", "доставка", "когда будет"),
            "payment_terms": ("оплат", "платеж", "наличн", "карт", "банковск", "сбербанк"),
            "warranty_terms": ("гарант", "возврат", "обмен", "сервис", "недостат", "претенз"),
        }
        return {
            fact
            for fact, keywords in fact_keywords.items()
            if any(keyword in lowered for keyword in keywords)
        }

    def _is_conversational_open(self, text: str) -> bool:
        normalized = " ".join(text.lower().strip().split())
        if not normalized:
            return False
        if normalized in _GREETING_PHRASES:
            return True
        return any(
            normalized == phrase or normalized.startswith(f"{phrase} ") or normalized.startswith(f"{phrase},")
            for phrase in _GREETING_PHRASES
            if phrase not in {"/start", "start", "hi", "hello"}
        )

    def _sources_cover_facts(self, sources: list[VerifiedSource], facts: set[str]) -> bool:
        if not sources:
            return False
        if not facts:
            return True
        for fact in facts:
            needed = FACT_TO_CONFIRMED_FIELDS.get(fact, {fact})
            if not any(self._confirmed_fields(source) & needed for source in sources):
                return False
        return True

    def _confirmed_fields(self, source: VerifiedSource) -> set[str]:
        raw = source.metadata.get("confirmed_fields", "")
        if not raw.strip():
            return set()
        return {part.strip() for part in raw.split(",") if part.strip()}

    def _is_hours_query(self, text: str) -> bool:
        lowered = text.lower()
        markers = (
            "режим",
            "час",
            "работ",
            "открыт",
            "график",
            "завтра",
            "сегодня",
            "выходн",
            "воскрес",
            "суббот",
        )
        return any(marker in lowered for marker in markers)

    def _is_location_query(self, text: str) -> bool:
        lowered = text.lower()
        markers = (
            "где наход",
            "где вы",
            "адрес",
            "забрать",
            "самовывоз",
            "пункт выдач",
            "магазин",
            "как добрать",
            "где забрать",
            "где получить",
        )
        return any(marker in lowered for marker in markers)

    def _pick_best_source(
        self,
        sources: list[VerifiedSource],
        user_message: str,
    ) -> VerifiedSource:
        if self._is_hours_query(user_message) and not self._is_location_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title}".lower()
                if "hours" in haystack or "режим" in haystack or "час" in haystack:
                    return source
        if self._is_location_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title} {source.content[:200]}".lower()
                if "shops" in haystack or "пункт" in haystack or "магазин" in haystack or "забрать" in haystack:
                    return source
        return sources[0]

    def _format_kb_answer(
        self,
        sources: list[VerifiedSource],
        user_message: str = "",
    ) -> str:
        # One best-matching source avoids dumping duplicate FAQ articles.
        source = self._pick_best_source(sources, user_message)
        title = source.title.strip()
        content = source.content.strip()
        if title and content:
            # Avoid "Title\nTitle ..." when content already starts with the title.
            if content.lower().startswith(title.lower()):
                return content
            return f"{title}\n{content}"
        return content or SAFE_HANDOFF_MESSAGE
