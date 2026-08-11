from app.core.constants import HandoffReason


# Dynamic commercial facts must never be published from old QA / manager chat as confirmed prices.
_DYNAMIC_HANDOFF_REASONS = {
    HandoffReason.PRICE_UNKNOWN,
    HandoffReason.AVAILABILITY_UNKNOWN,
}


def is_candidate_eligible(*, handoff_reason: HandoffReason | None, intent: str | None = None) -> bool:
    """Return True when a KnowledgeCandidate may be created for later human review.

    Price/stock-only handoffs are logged as events but must not become FAQ price facts.
    """
    if handoff_reason in _DYNAMIC_HANDOFF_REASONS:
        return False
    normalized_intent = (intent or "").strip().lower()
    if normalized_intent in {"price", "stock", "price_stock", "commercial_price"}:
        return False
    return True


def is_publishable_as_faq(candidate_intent: str | None) -> bool:
    """Approved candidates are published as static FAQ only — never as live price/stock."""
    normalized = (candidate_intent or "").strip().lower()
    return normalized not in {"price", "stock", "price_stock", "commercial_price"}
