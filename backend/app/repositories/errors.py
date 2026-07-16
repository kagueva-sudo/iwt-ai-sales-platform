from sqlalchemy.orm import Session

from app.db.models import ErrorLogModel


class ErrorLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, error_type: str, error_message: str, message_id: str | None = None) -> ErrorLogModel:
        model = ErrorLogModel(
            message_id=message_id,
            error_type=error_type,
            error_message=error_message,
        )
        self.session.add(model)
        return model
