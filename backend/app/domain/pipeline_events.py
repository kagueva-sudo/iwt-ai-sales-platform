from enum import StrEnum


class PipelineEventType(StrEnum):
    MESSAGE_RECEIVED = "message_received"
    SOURCES_SELECTED = "sources_selected"
    PROMPT_BUILT = "prompt_built"
    LLM_CALLED = "llm_called"
    VALIDATOR_DECISION = "validator_decision"
    DECISION_ROUTER = "decision_router"
    RESPONSE_SENT = "response_sent"
    HANDOFF = "handoff"
