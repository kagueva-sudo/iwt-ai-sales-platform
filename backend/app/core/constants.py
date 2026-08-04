from enum import StrEnum


class ChannelType(StrEnum):
    MAX = "max"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBSITE = "website"
    WEBSITE_FORM = "website_form"
    WEBSITE_CHAT = "website_chat"
    INTERNAL = "internal"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ProcessingStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    HANDOFF_REQUIRED = "handoff_required"
    FAILED = "failed"


class AIValidationStatus(StrEnum):
    APPROVED = "approved"
    NEEDS_DATA = "needs_data"
    HANDOFF_REQUIRED = "handoff_required"


class HandoffReason(StrEnum):
    NO_INFORMATION = "no_information"
    NO_CONFIRMED_DATA = "no_confirmed_data"
    PRICE_UNKNOWN = "price_unknown"
    AVAILABILITY_UNKNOWN = "availability_unknown"
    LLM_ERROR = "llm_error"
    TIMEOUT = "timeout"
    CLIENT_REQUEST_MANAGER = "client_request_manager"
    COMPLEX_REQUEST = "complex_request"
    COMPLEX_PROJECT = "complex_project"
    COMMERCIAL_OFFER = "commercial_offer"
    COMPLAINT = "complaint"
    DISCOUNT_REQUEST = "discount_request"
    UNKNOWN = "unknown"


SYSTEM_USER = "system"
DEFAULT_LANGUAGE = "ru"
