"""Email channel policy: always manager inbox with AI draft, never auto-reply."""

from app.core.constants import ChannelType, HandoffReason
from app.domain.processing import ProcessingDecision, ProcessingResult


def apply_email_inbox_policy(result: ProcessingResult) -> ProcessingResult:
    """Force EMAIL results into HANDOFF so /inbox shows an AI draft.

    Does not send SMTP. Manager reply is handled by ManagerQueueService.
    """
    if result.channel != ChannelType.EMAIL:
        return result

    draft = (result.response_text or "").strip()
    if result.decision == ProcessingDecision.ERROR:
        result.metadata.setdefault("email_policy", "error_passthrough")
        return result

    if result.decision == ProcessingDecision.RESPOND:
        result.decision = ProcessingDecision.HANDOFF
        if result.handoff_reason is None:
            result.handoff_reason = HandoffReason.EMAIL_INBOX_REVIEW
        result.metadata["email_policy"] = "respond_to_handoff"
    else:
        result.metadata.setdefault("email_policy", "handoff_keep")
        if result.handoff_reason is None:
            result.handoff_reason = HandoffReason.EMAIL_INBOX_REVIEW

    if draft:
        result.response_text = draft
    result.metadata["email_auto_send"] = "false"
    return result
