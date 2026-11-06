import re

from app.ai_core.commercial_facts import detect_requested_commercial_facts, normalize_for_intent
from app.ai_core.llm_provider import LLMProvider
from app.ai_core.prompts import (
    CARTRIDGE_CLARIFY_MESSAGE,
    CATEGORY_PRICE_NARROWING_MESSAGE_TEMPLATE,
    GREETING_MESSAGE,
    NO_BUYBACK_MESSAGE,
    PRODUCT_CLARIFY_MESSAGE,
    SAFE_HANDOFF_MESSAGE,
    STOCK_PRICE_GUIDANCE_MESSAGE,
    THANKS_MESSAGE,
)
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

_THANKS_PHRASES = (
    "спасибо",
    "благодарю",
    "спс",
    "thanks",
    "thank you",
)

_MANAGER_MARKERS = (
    "менеджер",
    "оператор",
    "живой человек",
    "свяжите с",
    "соедините",
    "позовите",
    "позвать менеджер",
    "нужен менеджер",
    "хочу менеджер",
)

_PRODUCT_MARKERS = (
    "товар",
    "ноутбук",
    "компьютер",
    "принтер",
    "монитор",
    "картридж",
    "сервер",
    "смартфон",
    "планшет",
    "мышь",
    "клавиатур",
)

_BUYBACK_STRONG = (
    "скупа",
    "скупк",
    "выкуп",
    "trade in",
    "tradein",
    "трейд ин",
    "трейдин",
)
_BUYBACK_VERBS = (
    "покупа",
    "купит",
    "принима",
    "берёт",
    "берет",
    "сдать",
    "сдаёт",
    "сдает",
    "сдаёте",
    "сдаете",
)
_BUYBACK_OBJECTS = (
    "бу",
    "ноутбук",
    "компьют",
    "техник",
    "телефон",
    "айфон",
    "планшет",
    "монитор",
    "видеокарт",
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
        user_text = prompt_context.user_message
        intent = self._classify_intent(user_text, prompt_context)
        requested_facts = detect_requested_commercial_facts(user_text)

        if intent == "greeting" and not requested_facts:
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=GREETING_MESSAGE,
                sources=[],
                metadata={"reason": "conversational_greeting", "intent": intent},
            )

        if intent == "thanks" and not requested_facts:
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=THANKS_MESSAGE,
                sources=[],
                metadata={"reason": "conversational_thanks", "intent": intent},
            )

        if intent == "manager_request":
            return ProcessingResult(
                decision=ProcessingDecision.HANDOFF,
                response_text=SAFE_HANDOFF_MESSAGE,
                handoff_reason=HandoffReason.CLIENT_REQUEST_MANAGER,
                sources=source_ids,
                metadata={"reason": "client_request_manager", "intent": intent},
            )

        if self._is_buyback_query(user_text):
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=self._buyback_answer(prompt_context.verified_sources),
                sources=source_ids,
                metadata={"reason": "no_buyback", "intent": "buyback"},
            )

        if not prompt_context.verified_sources:
            if intent in {"product_search", "product_question", "consultation"} and not requested_facts:
                if self._has_product_identifier(user_text) or self._history_mentions_product(prompt_context) and self._has_product_identifier(user_text):
                    return ProcessingResult(
                        decision=ProcessingDecision.RESPOND,
                        response_text=STOCK_PRICE_GUIDANCE_MESSAGE,
                        sources=[],
                        metadata={"reason": "product_followup_guidance", "intent": intent},
                    )
                answer = self._product_clarify_answer(user_text, prompt_context)
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=answer,
                    sources=[],
                    metadata={"reason": "product_clarify", "intent": intent},
                )
            if requested_facts and requested_facts <= {"price", "stock"}:
                if self._is_broad_category_price_query(user_text):
                    return ProcessingResult(
                        decision=ProcessingDecision.RESPOND,
                        response_text=self._category_price_narrowing_answer(user_text),
                        sources=[],
                        metadata={"reason": "category_price_narrowing", "intent": intent},
                    )
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=STOCK_PRICE_GUIDANCE_MESSAGE,
                    sources=[],
                    metadata={"reason": "stock_price_guidance", "intent": intent},
                )
            if intent == "unknown" or not requested_facts:
                return ProcessingResult(
                    decision=ProcessingDecision.NEEDS_MORE_DATA,
                    response_text=(
                        "Не совсем понял запрос. Уточните, пожалуйста: нужен подбор товара, "
                        "цена, наличие, доставка, оплата или связь с менеджером?"
                    ),
                    sources=[],
                    metadata={"reason": "clarify_unknown", "intent": intent},
                )
            return ProcessingResult(
                decision=ProcessingDecision.HANDOFF,
                response_text=SAFE_HANDOFF_MESSAGE,
                handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
                sources=[],
                metadata={"reason": "no_verified_sources", "intent": intent},
            )

        if (
            requested_facts
            and requested_facts <= {"price", "stock"}
            and not self._sources_cover_facts(prompt_context.verified_sources, requested_facts)
        ):
            if self._is_broad_category_price_query(user_text):
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=self._category_price_narrowing_answer(user_text),
                    sources=source_ids,
                    metadata={"reason": "category_price_narrowing", "intent": intent},
                )
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=self._stock_price_guidance_answer(prompt_context.verified_sources),
                sources=source_ids,
                metadata={"reason": "stock_price_guidance", "intent": intent},
            )

        try:
            draft = await self.llm_provider.generate_response(
                prompt_context.system_prompt,
                self._compose_llm_user_message(prompt_context),
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
                        user_text,
                    ),
                    sources=source_ids,
                    errors=[str(exc)],
                    metadata={"reason": "llm_fallback_kb", "intent": intent},
                )
            return ProcessingResult(
                decision=ProcessingDecision.ERROR,
                response_text=SAFE_HANDOFF_MESSAGE,
                handoff_reason=HandoffReason.LLM_ERROR,
                sources=source_ids,
                errors=[str(exc)],
                metadata={"intent": intent},
            )

        validation = self.validator.validate(ai_response, prompt_context.verified_sources)
        result = self._to_processing_result(ai_response, validation)
        result.metadata.setdefault("intent", intent)
        if (
            result.decision != ProcessingDecision.RESPOND
            and self._sources_cover_facts(prompt_context.verified_sources, requested_facts)
        ):
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=self._format_kb_answer(
                    prompt_context.verified_sources,
                    user_text,
                ),
                sources=source_ids,
                metadata={
                    "reason": "validator_fallback_kb",
                    "validation_reason": result.metadata.get("reason", validation.reason or ""),
                    "intent": intent,
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

    def _normalize_for_intent(self, text: str) -> str:
        return normalize_for_intent(text)

    def _detect_requested_commercial_facts(self, text: str) -> set[str]:
        return detect_requested_commercial_facts(text)

    def _classify_intent(self, text: str, prompt_context: PromptContext) -> str:
        normalized = self._normalize_for_intent(text)
        if not normalized:
            return "unknown"
        if self._is_conversational_open(text):
            return "greeting"
        if self._is_thanks(normalized):
            return "thanks"
        if self._is_manager_request(normalized):
            return "manager_request"
        if self._is_buyback_query(text):
            return "buyback"

        facts = detect_requested_commercial_facts(text)
        if "price" in facts:
            return "price_question"
        if "stock" in facts:
            return "availability_question"
        if "delivery_terms" in facts:
            return "delivery_question"
        if "payment_terms" in facts:
            return "payment_question"
        if "warranty_terms" in facts:
            return "warranty_question"
        if "characteristics" in facts:
            return "product_question"
        if self._mentions_product(normalized) or self._looks_like_product_followup(normalized, prompt_context):
            return "product_search"
        if any(token in normalized for token in ("консульт", "помогите выбрать", "что выбрать", "не знаю что")):
            return "consultation"
        if any(token in normalized for token in ("заказ", "заявк", "статус")):
            return "order_status"
        if any(token in normalized for token in ("компани", "о вас", "iwt", "адрес", "режим работ")):
            return "company_info"
        if any(token in normalized for token in ("жалоб", "претенз", "недовольн")):
            return "complaint"
        if self._is_vague_followup(normalized) and prompt_context.recent_messages:
            return "product_search"
        return "unknown"

    def _is_conversational_open(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        if not normalized:
            return False
        if normalized in _GREETING_PHRASES:
            return True
        return any(
            normalized == phrase or normalized.startswith(f"{phrase} ")
            for phrase in _GREETING_PHRASES
        )

    def _is_thanks(self, normalized: str) -> bool:
        return normalized in _THANKS_PHRASES or any(
            normalized == phrase or normalized.startswith(f"{phrase} ") for phrase in _THANKS_PHRASES
        )

    def _is_manager_request(self, normalized: str) -> bool:
        return any(marker in normalized for marker in _MANAGER_MARKERS)

    def _mentions_product(self, normalized: str) -> bool:
        return any(marker in normalized for marker in _PRODUCT_MARKERS)

    def _looks_like_product_followup(self, normalized: str, prompt_context: PromptContext) -> bool:
        if not prompt_context.recent_messages:
            return False
        if len(normalized.split()) <= 6 and re.search(r"[a-zа-яё]*\d|\d", normalized, re.IGNORECASE):
            history = " ".join(item.text.lower() for item in prompt_context.recent_messages[-6:])
            return any(marker in history for marker in _PRODUCT_MARKERS)
        return False

    def _is_vague_followup(self, normalized: str) -> bool:
        vague = (
            "подходящий вариант",
            "другой вариант",
            "есть другой",
            "что еще",
            "что ещё",
            "не знаю",
            "подскажите",
        )
        return any(marker in normalized for marker in vague)

    def _compose_llm_user_message(self, prompt_context: PromptContext) -> str:
        history = list(prompt_context.recent_messages or [])
        filtered = [
            item
            for item in history
            if not (
                item.role in {"user", "customer", "client"}
                and item.text.strip() == prompt_context.user_message.strip()
            )
        ]
        recent = filtered[-6:]
        if not recent and not prompt_context.active_product and not prompt_context.active_topic:
            return prompt_context.user_message

        lines: list[str] = []
        if prompt_context.active_topic:
            lines.append(f"Активная тема: {prompt_context.active_topic}")
        if prompt_context.active_product:
            lines.append(f"Активный товар: {prompt_context.active_product}")
        if recent:
            lines.append("История диалога:")
            for item in recent:
                role = "Клиент" if item.role in {"user", "customer", "client"} else "Ассистент"
                lines.append(f"{role}: {item.text}")
        lines.append(f"Текущее сообщение клиента: {prompt_context.user_message}")
        return "\n".join(lines)

    def _product_clarify_answer(self, text: str, prompt_context: PromptContext | None = None) -> str:
        normalized = self._normalize_for_intent(text)
        history = ""
        if prompt_context is not None:
            history = " ".join(item.text.lower() for item in prompt_context.recent_messages[-6:])
        if "картридж" in normalized or "картридж" in history:
            return CARTRIDGE_CLARIFY_MESSAGE
        return PRODUCT_CLARIFY_MESSAGE

    def _has_product_identifier(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        if re.search(r"\d{2,}", normalized):
            return True
        id_markers = ("артикул", "sku", "модель", "laserjet", "lenovo", "hp ", "asus", "acer")
        return any(marker in normalized for marker in id_markers)

    def _history_mentions_product(self, prompt_context: PromptContext) -> bool:
        history = " ".join(item.text.lower() for item in prompt_context.recent_messages[-6:])
        return any(marker in history for marker in _PRODUCT_MARKERS)

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

    def _stock_price_guidance_answer(self, sources: list[VerifiedSource]) -> str:
        for source in sources:
            haystack = f"{source.source_id} {source.title}".lower()
            if "stock-price" in haystack or "наличие" in haystack or "цена" in haystack:
                content = source.content.strip()
                if content:
                    return content
        return STOCK_PRICE_GUIDANCE_MESSAGE

    def _is_broad_category_price_query(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        lowered = normalized.lower()

        category_markers = (
            "ноутбук",
            "ноутбуки",
            "компьютер",
            "компьютеры",
            "пк",
            "телефон",
            "смартфон",
            "планшет",
            "монитор",
            "картридж",
            "картриджи",
            "принтер",
            "принтеры",
        )
        id_markers = (
            "артикул",
            "sku",
            "код",
            "модель",
            "бренд",
            "part",
            "серия",
        )

        has_category = any(marker in lowered for marker in category_markers)
        has_identifier = any(marker in lowered for marker in id_markers) or re.search(r"\d{3,}", lowered) is not None
        return has_category and not has_identifier

    def _category_price_narrowing_answer(self, text: str) -> str:
        normalized = self._normalize_for_intent(text)
        lowered = normalized.lower()

        if "картридж" in lowered:
            return CARTRIDGE_CLARIFY_MESSAGE

        category = "товара"
        for marker in (
            "ноутбуки",
            "ноутбук",
            "компьютеры",
            "компьютер",
            "пк",
            "телефоны",
            "телефон",
            "планшеты",
            "планшет",
            "принтеры",
            "принтер",
        ):
            if marker in lowered:
                category = marker
                break

        if category == "ноутбук":
            category = "ноутбуки"
        return CATEGORY_PRICE_NARROWING_MESSAGE_TEMPLATE.format(category=category)

    def _is_buyback_query(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        if any(marker in normalized for marker in _BUYBACK_STRONG):
            return True
        has_verb = any(verb in normalized for verb in _BUYBACK_VERBS)
        has_object = any(obj in normalized for obj in _BUYBACK_OBJECTS)
        return has_verb and has_object

    def _buyback_answer(self, sources: list[VerifiedSource]) -> str:
        for source in sources:
            haystack = f"{source.source_id} {source.title}".lower()
            if "buyback" in haystack or "скуп" in haystack or "выкуп" in haystack:
                content = source.content.strip()
                if content:
                    return content
        return NO_BUYBACK_MESSAGE

    def _is_sunday_query(self, text: str) -> bool:
        return "воскрес" in text.lower()

    def _is_lunch_query(self, text: str) -> bool:
        lowered = text.lower()
        return "обед" in lowered or "перерыв" in lowered

    def _pick_best_source(
        self,
        sources: list[VerifiedSource],
        user_message: str,
    ) -> VerifiedSource:
        if self._is_buyback_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title}".lower()
                if "buyback" in haystack or "скуп" in haystack or "выкуп" in haystack:
                    return source
        if self._is_sunday_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title} {source.content}".lower()
                if "sunday" in haystack or "hours-sunday" in haystack or (
                    "воскрес" in haystack and "нет" in source.content.lower()
                ):
                    return source
        if self._is_lunch_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title} {source.content}".lower()
                if "lunch" in haystack or "hours-lunch" in haystack or "без перерыва" in haystack:
                    return source
        if self._is_hours_query(user_message) and not self._is_location_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title}".lower()
                if (
                    "hours-full" in haystack
                    or "hours" in haystack
                    or "режим" in haystack
                    or "working_hours" in haystack
                ):
                    return source
        if self._is_location_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title} {source.content[:200]}".lower()
                if (
                    "shops" in haystack
                    or "company-shops" in haystack
                    or "пункт" in haystack
                    or "забрать" in haystack
                ):
                    return source
        return sources[0]

    def _format_kb_answer(
        self,
        sources: list[VerifiedSource],
        user_message: str = "",
    ) -> str:
        source = self._pick_best_source(sources, user_message)
        content = source.content.strip()
        return content or SAFE_HANDOFF_MESSAGE

