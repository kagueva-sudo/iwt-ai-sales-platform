from sqlalchemy.orm import Session

from app.db.models import AILogModel


class AILogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, message_id: str, request_text: str, response_text: str, validation_status: str) -> AILogModel:
        model = AILogModel(
            message_id=message_id,
            request_text=request_text,
            response_text=response_text,
            validation_status=validation_status,
        )
        self.session.add(model)
        return model
