import json
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.contracts.manager_queue_repository import ManagerQueueRepository
from app.core.constants import ChannelType, HandoffReason
from app.db.models import ManagerQueueModel
from app.db.session import SessionLocal
from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus


class InMemoryManagerQueueRepository(ManagerQueueRepository):
    def __init__(self) -> None:
        self._items: dict[str, ManagerQueueItem] = {}

    async def add(self, item: ManagerQueueItem) -> ManagerQueueItem:
        self._items[item.request_id] = item
        return item

    async def get(self, request_id: str) -> ManagerQueueItem | None:
        return self._items.get(request_id)

    async def update_status(self, request_id: str, status: ManagerQueueStatus) -> ManagerQueueItem | None:
        item = self._items.get(request_id)
        if item is None:
            return None
        item.status = status
        return item

    async def list_by_status(self, status: ManagerQueueStatus) -> list[ManagerQueueItem]:
        return [item for item in self._items.values() if item.status == status]

    async def list_all(self) -> list[ManagerQueueItem]:
        return list(self._items.values())


class SqlAlchemyManagerQueueRepository(ManagerQueueRepository):
    """PostgreSQL/SQLite-backed ManagerQueueRepository via SQLAlchemy."""

    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal

    async def add(self, item: ManagerQueueItem) -> ManagerQueueItem:
        with self._session_factory() as session:
            session.add(self._to_model(item))
            session.commit()
        return item

    async def get(self, request_id: str) -> ManagerQueueItem | None:
        with self._session_factory() as session:
            model = session.get(ManagerQueueModel, request_id)
            return self._to_domain(model) if model is not None else None

    async def update_status(self, request_id: str, status: ManagerQueueStatus) -> ManagerQueueItem | None:
        with self._session_factory() as session:
            model = session.get(ManagerQueueModel, request_id)
            if model is None:
                return None
            model.status = status.value
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    async def list_by_status(self, status: ManagerQueueStatus) -> list[ManagerQueueItem]:
        with self._session_factory() as session:
            rows = (
                session.query(ManagerQueueModel)
                .filter(ManagerQueueModel.status == status.value)
                .order_by(ManagerQueueModel.created_at.desc())
                .all()
            )
            return [self._to_domain(row) for row in rows]

    async def list_all(self) -> list[ManagerQueueItem]:
        with self._session_factory() as session:
            rows = session.query(ManagerQueueModel).order_by(ManagerQueueModel.created_at.desc()).all()
            return [self._to_domain(row) for row in rows]

    def _to_model(self, item: ManagerQueueItem) -> ManagerQueueModel:
        return ManagerQueueModel(
            request_id=item.request_id,
            channel=item.channel.value,
            customer_name=item.customer_name,
            customer_contact=item.customer_contact,
            conversation_history=json.dumps(item.conversation_history, ensure_ascii=False),
            ai_response=item.ai_response,
            handoff_reason=item.handoff_reason.value,
            status=item.status.value,
            created_at=item.created_at,
        )

    def _to_domain(self, model: ManagerQueueModel) -> ManagerQueueItem:
        history_raw = model.conversation_history or "[]"
        try:
            history = json.loads(history_raw)
            if not isinstance(history, list):
                history = []
        except json.JSONDecodeError:
            history = [line for line in history_raw.split("\n") if line]

        return ManagerQueueItem(
            request_id=model.request_id,
            channel=ChannelType(model.channel),
            customer_name=model.customer_name,
            customer_contact=model.customer_contact,
            conversation_history=[str(part) for part in history],
            ai_response=model.ai_response,
            handoff_reason=HandoffReason(model.handoff_reason),
            status=ManagerQueueStatus(model.status),
            created_at=model.created_at,
        )
