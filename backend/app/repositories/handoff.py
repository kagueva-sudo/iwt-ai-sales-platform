from sqlalchemy.orm import Session

from app.db.models import HandoffModel
from app.domain.handoff import HandoffCase


class HandoffRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, handoff_case: HandoffCase, external_id: str | None = None) -> HandoffModel:
        model = HandoffModel(
            id=handoff_case.id,
            external_id=external_id,
            channel=handoff_case.channel.value,
            customer_id=handoff_case.customer_id,
            customer_contact=handoff_case.customer_contact,
            message=handoff_case.message,
            reason=handoff_case.reason.value,
            ai_recommendation=handoff_case.ai_recommendation,
            created_at=handoff_case.created_at,
        )
        self.session.add(model)
        return model
