from enum import StrEnum


class ChannelType(StrEnum):
    MAX = "max"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBSITE = "website"
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
    REJECTED = "rejected"


class HandoffReason(StrEnum):
    NO_CONFIRMED_DATA = "no_confirmed_data"
    COMPLEX_PROJECT = "complex_project"
    COMMERCIAL_OFFER = "commercial_offer"
    COMPLAINT = "complaint"
    DISCOUNT_REQUEST = "discount_request"
    UNKNOWN = "unknown"


SYSTEM_USER = "system"
DEFAULT_LANGUAGE = "ru"
