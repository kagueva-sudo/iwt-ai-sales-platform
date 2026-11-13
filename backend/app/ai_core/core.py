import re

from app.ai_core.commercial_facts import detect_requested_commercial_facts, normalize_for_intent
from app.ai_core.llm_provider import LLMProvider
from app.ai_core.prompts import (
    CARTRIDGE_CLARIFY_MESSAGE,
    CARTRIDGE_REFILL_MESSAGE,
    CATEGORY_PRICE_NARROWING_MESSAGE_TEMPLATE,
    CONTACTS_MESSAGE,
    GREETING_MESSAGE,
    NO_BUYBACK_MESSAGE,
    PRODUCT_CLARIFY_MESSAGE,
    SAFE_HANDOFF_MESSAGE,
    SERVICE_DEPT_CONTACT_MESSAGE,
    SERVICE_HOURS_MESSAGE,
    SHOPS_ADDRESS_MESSAGE,
    STOCK_PRICE_GUIDANCE_MESSAGE,
    THANKS_MESSAGE,
    WORKING_HOURS_MESSAGE,
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

# Client rejects the last product suggestion → hand off, do not invent another answer.
_PRODUCT_REJECTION_MARKERS = (
    "не то",
    "не тот",
    "не та",
    "не те",
    "не то что",
    "не то,",
    "это не то",
    "это, не то",
    "не подходит",
    "неправильн",
    "не то нужно",
    "не то надо",
    "совсем не то",
    "не то совсем",
    "другой нужен",
    "не то предложение",
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
    "ибп",
    "бесперебойн",
    "источник бесперебой",
    "видеокарт",
    "ssd",
    "hdd",
    "роутер",
    "коммутатор",
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
            # Always greet back — even mid-dialog. Suppressing to "Чем ещё..."
            # felt abrupt and broke the expected greeting in MAX/WhatsApp.
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

        if intent == "product_rejection" or self._is_product_rejection(user_text, prompt_context):
            return ProcessingResult(
                decision=ProcessingDecision.HANDOFF,
                response_text=SAFE_HANDOFF_MESSAGE,
                handoff_reason=HandoffReason.COMPLEX_REQUEST,
                sources=source_ids,
                metadata={"reason": "product_rejection", "intent": "product_rejection"},
            )

        if self._is_buyback_query(user_text):
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=self._buyback_answer(prompt_context.verified_sources),
                sources=source_ids,
                metadata={"reason": "no_buyback", "intent": "buyback"},
            )

        if self._is_refill_query(user_text):
            if prompt_context.verified_sources:
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=self._format_kb_answer(
                        prompt_context.verified_sources,
                        user_text,
                    ),
                    sources=source_ids,
                    metadata={"reason": "refill_kb", "intent": "service_refill"},
                )
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=CARTRIDGE_REFILL_MESSAGE,
                sources=[],
                metadata={"reason": "refill_fallback", "intent": "service_refill"},
            )

        # Hours about service center first — not the services catalogue.
        if self._is_hours_query(user_text) and self._mentions_service_center(user_text):
            service_hours_sources = [
                source
                for source in prompt_context.verified_sources
                if self._source_looks_like_service_hours(source)
            ]
            if service_hours_sources:
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=self._format_kb_answer(service_hours_sources, user_text),
                    sources=[source.source_id for source in service_hours_sources],
                    metadata={"reason": "service_hours_kb", "intent": "company_info"},
                )
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=SERVICE_HOURS_MESSAGE,
                sources=[],
                metadata={"reason": "service_hours_fallback", "intent": "company_info"},
            )

        if self._is_service_dept_query(user_text):
            if prompt_context.verified_sources:
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=self._format_kb_answer(
                        prompt_context.verified_sources,
                        user_text,
                    ),
                    sources=source_ids,
                    metadata={"reason": "service_dept_kb", "intent": "service_contact"},
                )
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=SERVICE_DEPT_CONTACT_MESSAGE,
                sources=[],
                metadata={"reason": "service_dept_fallback", "intent": "service_contact"},
            )

        # FAQ / company facts — answer from Knowledge Base (or static fallback).
        faq_intents = {
            "company_info",
            "delivery_question",
            "payment_question",
            "warranty_question",
            "service_question",
        }
        if (
            intent in faq_intents
            or self._is_hours_query(user_text)
            or self._is_location_query(user_text)
            or self._is_contacts_query(user_text)
        ):
            answer_sources = list(prompt_context.verified_sources)
            if intent == "payment_question":
                payment_sources = [
                    source
                    for source in answer_sources
                    if self._source_looks_like_payment(source)
                ]
                if payment_sources:
                    answer_sources = payment_sources
                else:
                    answer_sources = []
            if self._is_hours_query(user_text):
                hours_sources = [
                    source
                    for source in answer_sources
                    if self._source_looks_like_hours(source)
                ]
                if hours_sources:
                    answer_sources = hours_sources
            if answer_sources:
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=self._format_kb_answer(answer_sources, user_text),
                    sources=[source.source_id for source in answer_sources],
                    metadata={"reason": "faq_kb", "intent": intent},
                )
            fallback = self._faq_fallback_answer(user_text, intent)
            if fallback:
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=fallback,
                    sources=[],
                    metadata={"reason": "faq_fallback", "intent": intent},
                )

        catalog_products = self._catalog_product_sources(prompt_context.verified_sources)
        if catalog_products and (
            intent in {"product_search", "product_question", "availability_question", "price_question"}
            or (requested_facts and requested_facts <= {"price", "stock"})
        ):
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=self._format_catalog_products_answer(
                    catalog_products,
                    user_text=user_text,
                ),
                sources=[item.source_id for item in catalog_products],
                metadata={"reason": "website_catalog_products", "intent": intent},
            )

        if not prompt_context.verified_sources:
            if intent in {"product_search", "product_question", "consultation"} and not requested_facts:
                if self._has_product_identifier(user_text) or self._history_mentions_product(prompt_context) and self._has_product_identifier(user_text):
                    return ProcessingResult(
                        decision=ProcessingDecision.HANDOFF,
                        response_text=SAFE_HANDOFF_MESSAGE,
                        handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
                        sources=[],
                        metadata={"reason": "product_followup_handoff", "intent": intent},
                    )
                answer = self._product_clarify_answer(user_text, prompt_context)
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=answer,
                    sources=[],
                    metadata={"reason": "product_clarify", "intent": intent},
                )
            if requested_facts and requested_facts <= {"price", "stock"}:
                if "картридж" in self._normalize_for_intent(user_text) and "заправ" not in self._normalize_for_intent(user_text):
                    return ProcessingResult(
                        decision=ProcessingDecision.RESPOND,
                        response_text=CARTRIDGE_CLARIFY_MESSAGE,
                        sources=[],
                        metadata={"reason": "cartridge_clarify", "intent": intent},
                    )
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=(
                        "На сайте сейчас не нашёл точного совпадения. "
                        "Уточните модель/бренд или напишите — передам запрос менеджеру. "
                        "Каталог: https://www.iwt.ru/"
                    ),
                    sources=[],
                    metadata={"reason": "stock_price_no_catalog_hits", "intent": intent},
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
            if "картридж" in self._normalize_for_intent(user_text) and "заправ" not in self._normalize_for_intent(user_text):
                return ProcessingResult(
                    decision=ProcessingDecision.RESPOND,
                    response_text=CARTRIDGE_CLARIFY_MESSAGE,
                    sources=source_ids,
                    metadata={"reason": "cartridge_clarify", "intent": intent},
                )
            return ProcessingResult(
                decision=ProcessingDecision.RESPOND,
                response_text=(
                    "На сайте сейчас не нашёл точного совпадения по наличию/цене. "
                    "Уточните модель или артикул — либо передам запрос менеджеру. "
                    "Каталог: https://www.iwt.ru/"
                ),
                sources=source_ids,
                metadata={"reason": "stock_price_no_catalog_cover", "intent": intent},
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
            and requested_facts
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
        if self._is_product_rejection(text, prompt_context):
            return "product_rejection"
        if self._is_buyback_query(text):
            return "buyback"
        if self._is_refill_query(text) or self._is_service_dept_query(text):
            return "service_question"

        # Commercial facts before hours/location: "Вы работаете по безналу?"
        # contains "работаете" but is a payment question, not schedule.
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

        if self._is_hours_query(text) and not self._mentions_product(normalized):
            return "company_info"
        if self._is_location_query(text) or self._is_contacts_query(text):
            return "company_info"
        if self._mentions_product(normalized) or self._looks_like_product_followup(normalized, prompt_context):
            return "product_search"
        if any(token in normalized for token in ("консульт", "помогите выбрать", "что выбрать", "не знаю что")):
            return "consultation"
        if any(token in normalized for token in ("заказ", "заявк", "статус")):
            return "order_status"
        if any(token in normalized for token in ("компани", "о вас", "iwt", "адрес", "режим работ", "работаете")):
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
        # Only pure greetings — never treat product questions as greetings.
        return normalized in _GREETING_PHRASES

    def _is_thanks(self, normalized: str) -> bool:
        return normalized in _THANKS_PHRASES or any(
            normalized == phrase or normalized.startswith(f"{phrase} ") for phrase in _THANKS_PHRASES
        )

    def _is_manager_request(self, normalized: str) -> bool:
        return any(marker in normalized for marker in _MANAGER_MARKERS)

    def _is_product_rejection(self, text: str, prompt_context: PromptContext) -> bool:
        normalized = self._normalize_for_intent(text)
        if not normalized:
            return False
        if not any(marker in normalized for marker in _PRODUCT_REJECTION_MARKERS):
            return False
        # Reject only in product context (recent client/assistant talk about goods).
        if self._mentions_product(normalized):
            return True
        if self._history_mentions_product(prompt_context):
            return True
        history = " ".join(item.text.lower() for item in prompt_context.recent_messages[-6:])
        return any(
            token in history
            for token in ("в наличии", "на сайте iwt", "вариант", "цена", "артикул", "pc-", "картридж")
        )

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
        # Empty facts must not unlock KB dump (that invented warranty after «не то»).
        if not facts:
            return False
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
        normalized = self._normalize_for_intent(text)
        strong = (
            "режим работ",
            "час работ",
            "часы работ",
            "график",
            "во сколько",
            "до скольки",
            "до скольк",
            "открыт",
            "закрыт",
            "выходн",
            "воскрес",
            "суббот",
        )
        # Explicit schedule phrases win even if text also mentions сервис/оплату.
        if any(marker in normalized for marker in strong):
            return True
        # "Вы работаете по безналу?" — не про график.
        if detect_requested_commercial_facts(text) & {
            "payment_terms",
            "delivery_terms",
            "price",
            "stock",
            "warranty_terms",
        }:
            return False
        if any(token in normalized for token in ("работаете", "работаем", "работает", "работа")):
            return any(
                marker in normalized
                for marker in (
                    "завтра",
                    "сегодня",
                    "сейчас",
                    "режим",
                    "час",
                    "график",
                    "выходн",
                    "воскрес",
                    "суббот",
                    "пн",
                    "вт",
                    "ср",
                    "чт",
                    "пт",
                    "сб",
                    "вс",
                )
            )
        return False

    def _is_location_query(self, text: str) -> bool:
        lowered = text.lower()
        markers = (
            "где наход",
            "где вы",
            "адрес",
            "адресе",
            "забрать",
            "самовывоз",
            "пункт выдач",
            "магазин",
            "как добрать",
            "где забрать",
            "где получить",
            "где офис",
            "как вас найти",
        )
        return any(marker in lowered for marker in markers)

    def _is_contacts_query(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        markers = (
            "контакт",
            "телефон",
            "почта",
            "email",
            "e-mail",
            "whatsapp",
            "ватсап",
            "напишите номер",
        )
        return any(marker in normalized for marker in markers)

    def _is_refill_query(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        has_refill = "заправ" in normalized
        has_cartridge = "картридж" in normalized or "тонер" in normalized or "лазер" in normalized
        return has_refill and (has_cartridge or has_refill)

    def _mentions_service_center(self, text: str) -> bool:
        normalized = self._normalize_for_intent(text)
        markers = (
            "сервисный центр",
            "сервис центр",
            "сервисцентра",
            "сервисный отдел",
            "технический отдел",
            "гарантийный отдел",
            "отдел гарантии",
        )
        if any(marker in normalized for marker in markers):
            return True
        # Short forms: «сервис» / «асц», but not «сервер».
        tokens = normalized.split()
        return "сервис" in tokens or "асц" in tokens

    def _is_service_dept_query(self, text: str) -> bool:
        # «до скольки работает сервис» — это режим, не каталог услуг.
        if self._is_hours_query(text):
            return False
        normalized = self._normalize_for_intent(text)
        markers = (
            "технический отдел",
            "сервисный отдел",
            "отдел гарантии",
            "гарантийный отдел",
            "сервисный центр",
            "сервис центр",
            "техподдерж",
            "техническая поддержка",
            "связаться с сервисом",
            "номер сервиса",
            "телефон сервиса",
        )
        return any(marker in normalized for marker in markers)

    def _source_looks_like_hours(self, source: VerifiedSource) -> bool:
        haystack = f"{source.source_id} {source.title}".lower()
        return any(
            marker in haystack
            for marker in ("hours-", "hours", "режим", "working_hours", "график")
        )

    def _source_looks_like_service_hours(self, source: VerifiedSource) -> bool:
        haystack = f"{source.source_id} {source.title} {source.content[:240]}".lower()
        if "hours-service" in haystack:
            return True
        return self._source_looks_like_hours(source) and (
            "сервис" in haystack or "ремонт" in haystack
        )

    def _source_looks_like_payment(self, source: VerifiedSource) -> bool:
        haystack = f"{source.source_id} {source.title} {source.content[:300]}".lower()
        return any(
            marker in haystack
            for marker in ("payment", "оплат", "безнал", "сбербанк", "наличн", "картой")
        )

    def _faq_fallback_answer(self, text: str, intent: str) -> str | None:
        if self._is_refill_query(text):
            return CARTRIDGE_REFILL_MESSAGE
        if self._is_hours_query(text) and self._mentions_service_center(text):
            return SERVICE_HOURS_MESSAGE
        if self._is_service_dept_query(text) or intent == "service_question":
            return SERVICE_DEPT_CONTACT_MESSAGE
        if intent == "payment_question" or "payment_terms" in detect_requested_commercial_facts(text):
            return (
                "Способы оплаты IWT.ru:\n\n"
                "1) Наличными — в магазине или курьеру при получении.\n"
                "2) Банковской картой — через ПАО Сбербанк на сайте.\n"
                "3) Безналичный расчёт — для юрлиц и ИП (счёт / договор). "
                "Корпоративный отдел: 8 (8722) 56-06-06, info@iwt.ru. "
                "Оформление заказа также в WhatsApp и MAX: +7 903 488-00-77.\n\n"
                "Подробнее: https://www.iwt.ru/payments/"
            )
        if intent == "delivery_question":
            return (
                "Доставка по Махачкале и Каспийску — курьером. "
                "По России — транспортными компаниями. "
                "Самовывоз: Махачкала, ул. Азиза Алиева, 17А и Каспийск, ул. Ленина, д. 6. "
                "Точную стоимость и срок уточнит менеджер."
            )
        if self._is_hours_query(text):
            return WORKING_HOURS_MESSAGE
        if self._is_location_query(text):
            return SHOPS_ADDRESS_MESSAGE
        if self._is_contacts_query(text) or intent == "company_info":
            if self._is_contacts_query(text) and not self._is_location_query(text):
                return CONTACTS_MESSAGE
            if intent == "company_info" and self._is_location_query(text):
                return SHOPS_ADDRESS_MESSAGE
        if intent == "warranty_question":
            return (
                "На технику действует официальная гарантия производителя "
                "(обычно от 12 до 36 месяцев). Гарантийное обслуживание — через сервисный центр IWT. "
                "Контакты: 8 (8722) 56-06-06 доб. 2, сервисный центр 8 928 058-06-06, info@iwt.ru."
            )
        return None

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
        if self._is_refill_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title}".lower()
                if "refill" in haystack or "заправ" in haystack:
                    return source
        if self._is_hours_query(user_message) and self._mentions_service_center(user_message):
            for source in sources:
                if self._source_looks_like_service_hours(source):
                    return source
            for source in sources:
                if self._source_looks_like_hours(source):
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
        if "payment_terms" in detect_requested_commercial_facts(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title} {source.content[:240]}".lower()
                if (
                    "payment" in haystack
                    or "оплат" in haystack
                    or "безнал" in haystack
                    or "сбербанк" in haystack
                ):
                    return source
        if self._is_hours_query(user_message) and not self._is_location_query(user_message):
            for source in sources:
                if self._source_looks_like_hours(source):
                    return source
        if self._is_service_dept_query(user_message):
            for source in sources:
                haystack = f"{source.source_id} {source.title} {source.content[:240]}".lower()
                if (
                    "services-contact" in haystack
                    or "services-overview" in haystack
                    or "сервисн" in haystack
                    or "техническ" in haystack
                    or "928 058" in haystack
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

    def _catalog_product_sources(self, sources: list[VerifiedSource]) -> list[VerifiedSource]:
        products: list[VerifiedSource] = []
        for source in sources:
            meta = source.metadata or {}
            confirmed = {part.strip() for part in str(meta.get("confirmed_fields", "")).split(",") if part.strip()}
            is_store = meta.get("source") == "website_store" or source.source_type == "website_provider"
            looks_like_product = bool(meta.get("price") or meta.get("source_url") or "price" in confirmed)
            if is_store and looks_like_product:
                products.append(source)
        return products

    def _format_catalog_products_answer(
        self,
        sources: list[VerifiedSource],
        *,
        user_text: str = "",
    ) -> str:
        intro = "На сайте IWT есть такие варианты:"
        low = (user_text or "").lower().replace("ё", "е")
        if re.search(r"(?<![а-яa-z0-9_])ибп(?![а-яa-z0-9_])", low) or "бесперебой" in low or re.search(
            r"(?<![а-яa-z0-9_])ups(?![а-яa-z0-9_])", low
        ):
            intro = (
                "ИБП (источник бесперебойного питания) — на сайте IWT есть такие варианты:"
            )
        lines = [intro]
        for source in sources[:5]:
            meta = source.metadata or {}
            title = source.title.strip() or "Товар"
            price = meta.get("price")
            url = meta.get("source_url") or ""
            if price:
                try:
                    price_txt = f"{float(price):,.0f}".replace(",", " ")
                    lines.append(f"• {title} — {price_txt} руб.")
                except ValueError:
                    lines.append(f"• {title}")
            else:
                lines.append(f"• {title}")
            if url:
                lines.append(f"  {url}")
        lines.append(
            "\nЕсли нужна помощь с подбором конкретной модели — напишите параметры "
            "или попросите связать с менеджером."
        )
        return "\n".join(lines)

