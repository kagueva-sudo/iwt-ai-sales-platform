from app.core.constants import ChannelType, HandoffReason
from app.domain.processing import ProcessingDecision, ProcessingResult
from app.services.email_inbox_policy import apply_email_inbox_policy


def test_email_respond_becomes_handoff_draft() -> None:
    result = ProcessingResult(
        decision=ProcessingDecision.RESPOND,
        response_text="Черновик про оплату",
        channel=ChannelType.EMAIL,
    )
    out = apply_email_inbox_policy(result)
    assert out.decision == ProcessingDecision.HANDOFF
    assert out.response_text == "Черновик про оплату"
    assert out.handoff_reason == HandoffReason.EMAIL_INBOX_REVIEW
    assert out.metadata.get("email_auto_send") == "false"


def test_non_email_unchanged() -> None:
    result = ProcessingResult(
        decision=ProcessingDecision.RESPOND,
        response_text="ok",
        channel=ChannelType.MAX,
    )
    out = apply_email_inbox_policy(result)
    assert out.decision == ProcessingDecision.RESPOND
    assert out.response_text == "ok"
