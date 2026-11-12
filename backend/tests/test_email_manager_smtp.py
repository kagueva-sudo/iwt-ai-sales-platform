import pytest

from app.channel_adapters.email_adapter import EmailChannelAdapter
from app.core.constants import ChannelType, HandoffReason
from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus
from app.domain.messages import Message
from app.repositories.manager_queue import InMemoryManagerQueueRepository
from app.services.manager_queue_service import ManagerQueueService


pytestmark = pytest.mark.asyncio


class StubSmtpAdapter(EmailChannelAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.manager_replies: list[Message] = []

    async def send_message(self, message: Message) -> str:
        self.sent.append(message)
        if message.metadata.get("outbound_kind") == "manager_reply":
            self.manager_replies.append(message)
        return message.id


async def test_done_sends_smtp_for_email_channel() -> None:
    repo = InMemoryManagerQueueRepository()
    adapter = StubSmtpAdapter()
    service = ManagerQueueService(repo, email_adapter=adapter)
    item = ManagerQueueItem(
        channel=ChannelType.EMAIL,
        customer_contact="client@example.com",
        conversation_history=["Subject: Привет\n\nНужна консультация"],
        ai_response="Черновик AI",
        handoff_reason=HandoffReason.EMAIL_INBOX_REVIEW,
        request_id="email-1",
        email_message_id="<id-1@example.com>",
        email_subject="Привет",
    )
    await repo.add(item)

    updated = await service.update_status(
        "email-1",
        ManagerQueueStatus.DONE,
        manager_answer="Здравствуйте! Помогу с подбором.",
    )
    assert updated is not None
    assert updated.status == ManagerQueueStatus.DONE
    assert len(adapter.manager_replies) == 1
    sent = adapter.manager_replies[0]
    assert sent.customer_contact == "client@example.com"
    assert "Помогу с подбором" in sent.text
    assert sent.metadata["email_message_id"] == "<id-1@example.com>"


async def test_done_without_answer_skips_smtp() -> None:
    repo = InMemoryManagerQueueRepository()
    adapter = StubSmtpAdapter()
    service = ManagerQueueService(repo, email_adapter=adapter)
    await repo.add(
        ManagerQueueItem(
            channel=ChannelType.EMAIL,
            customer_contact="client@example.com",
            conversation_history=["hi"],
            ai_response="draft",
            handoff_reason=HandoffReason.EMAIL_INBOX_REVIEW,
            request_id="email-2",
        )
    )
    await service.update_status("email-2", ManagerQueueStatus.DONE, manager_answer="  ")
    assert adapter.manager_replies == []
