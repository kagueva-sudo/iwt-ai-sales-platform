from sqlalchemy.orm import Session

from app.db.models import MessageModel
from app.domain.messages import Message


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, message: Message) -> MessageModel:
        model = MessageModel(
            id=message.id,
            channel=message.channel.value,
            direction=message.direction.value,
            customer_id=message.customer_id,
            customer_contact=message.customer_contact,
            text=message.text,
            status=message.status.value,
            created_at=message.created_at,
        )
        self.session.add(model)
        return model
