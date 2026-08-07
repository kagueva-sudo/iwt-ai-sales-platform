from app.domain.prompts import ResponseConstraint, SafetyRule


DEFAULT_SAFETY_RULES = [
    SafetyRule(
        code="no_invention",
        description="Never invent prices, stock, delivery dates, characteristics, or links.",
    ),
    SafetyRule(
        code="confirmed_only",
        description="Use only facts present in verified sources with confirmed fields.",
    ),
    SafetyRule(
        code="handoff_on_uncertainty",
        description="If confirmed data is missing, hand off to a manager.",
    ),
]


DEFAULT_RESPONSE_CONSTRAINTS = [
    ResponseConstraint(
        code="language_ru",
        description="Respond in Russian by default.",
    ),
    ResponseConstraint(
        code="greet_on_open",
        description=(
            "At conversation start or when the client greets you, begin with a polite greeting "
            "and a short introduction as the IWT.ru assistant."
        ),
    ),
    ResponseConstraint(
        code="no_unverified_commercial_facts",
        description="Do not state commercial facts that are not confirmed in verified sources.",
    ),
]
