from app.core.constants import ChannelType, HandoffReason
from app.domain.handoff import HandoffCase
from app.providers.crm_provider import CRMProvider


class HandoffService:
    def __init__(self, crm_provider: CRMProvider) -> None:
        self.crm_provider = crm_provider

    async def create_handoff(
        self,
        channel: ChannelType,
        message: str,
        reason: HandoffReason,
        customer_id: str | None = None,
        customer_contact: str | None = None,
        history: list[str] | None = None,
        ai_recommendation: str | None = None,
    ) -> str:
        handoff_case = HandoffCase(
            channel=channel,
            message=message,
            reason=reason,
            customer_id=customer_id,
            customer_contact=customer_contact,
            history=history or [],
            ai_recommendation=ai_recommendation,
        )
        return await self.crm_provider.create_handoff_case(handoff_case)
