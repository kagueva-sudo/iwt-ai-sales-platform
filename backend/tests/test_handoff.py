import pytest

from app.core.constants import ChannelType, HandoffReason
from app.providers.mock_providers import MockCRMProvider
from app.services.handoff_service import HandoffService


@pytest.mark.asyncio
async def test_handoff_service_creates_case_in_crm_provider() -> None:
    service = HandoffService(MockCRMProvider())

    external_id = await service.create_handoff(
        channel=ChannelType.MAX,
        message="Нужна цена товара",
        reason=HandoffReason.NO_CONFIRMED_DATA,
        customer_contact="@client",
        ai_recommendation="Нет подтвержденных данных.",
    )

    assert external_id.startswith("mock-crm-")
