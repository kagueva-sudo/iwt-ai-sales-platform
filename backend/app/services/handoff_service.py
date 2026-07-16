from app.core.constants import ChannelType, HandoffReason
from app.domain.handoff import HandoffCase
from app.providers.crm_provider import CRMProvider
from app.repositories.handoff import HandoffRepository


class HandoffService:
    def __init__(self, crm_provider: CRMProvider, handoff_repository: HandoffRepository | None = None) -> None:
        self.crm_provider = crm_provider
        self.handoff_repository = handoff_repository

    async def create_handoff(
        self,
        channel: ChannelType,
        message: str,
        reason: HandoffReason,
        customer_id: str | None = None,
        customer_contact: str | None = None,
        history: list[str] | None = None,
        ai_response: str | None = None,
        ai_recommendation: str | None = None,
    ) -> str:
        handoff_case = HandoffCase(
            channel=channel,
            message=message,
            reason=reason,
            customer_id=customer_id,
            customer_contact=customer_contact,
            history=history or [],
            ai_response=ai_response,
            ai_recommendation=ai_recommendation,
        )
        handoff_model = None
        if self.handoff_repository is not None:
            handoff_model = self.handoff_repository.add(handoff_case)
            self.handoff_repository.session.flush()

        external_id = await self.crm_provider.create_handoff_case(handoff_case)
        if handoff_model is not None:
            handoff_model.external_id = external_id
            self.handoff_repository.session.flush()

        return external_id
