"""Shared commercial-fact heuristics for AICore and AIValidator.

Word-safe markers: substring "карт" must not match "картридж".
"""

from __future__ import annotations

import re

_PUNCT_RE = re.compile(r"[^\w\sа-яёА-ЯЁ]+", re.UNICODE)
_CARD_RE = re.compile(r"(?<![а-яё])карт(?!ридж)", re.IGNORECASE)


def normalize_for_intent(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    lowered = lowered.replace("б/у", " бу ").replace("б\\у", " бу ").replace("б у", " бу ")
    lowered = _PUNCT_RE.sub(" ", lowered)
    return " ".join(lowered.split())


def detect_requested_commercial_facts(text: str) -> set[str]:
    lowered = normalize_for_intent(text)
    fact_keywords: dict[str, tuple[str, ...]] = {
        "price": ("цена", "стоимость", "сколько стоит", "прайс"),
        "stock": ("налич", "остат", "на складе", "в продаже", "в наличии"),
        "characteristics": ("характерист", "параметр", "мощность", "размер", "габарит"),
        "delivery_terms": ("срок", "поставка", "доставка", "когда будет"),
        "warranty_terms": ("гарант", "возврат", "обмен", "сервис", "недостат", "претенз"),
    }
    found = {
        fact
        for fact, keywords in fact_keywords.items()
        if any(keyword in lowered for keyword in keywords)
    }
    if _looks_like_payment(lowered):
        found.add("payment_terms")
    return found


def _looks_like_payment(normalized: str) -> bool:
    payment_markers = (
        "оплат",
        "платеж",
        "наличн",
        "банковск",
        "сбербанк",
        "безнал",
        "по карте",
        "картой",
    )
    if any(marker in normalized for marker in payment_markers):
        return True
    # "карта/карты/карте" but never "картридж*"
    return _CARD_RE.search(normalized) is not None

