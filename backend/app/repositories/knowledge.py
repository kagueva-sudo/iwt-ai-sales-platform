import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts.knowledge_repository import KnowledgeRepository
from app.db.models import KnowledgeItemModel
from app.db.session import SessionLocal
from app.domain.knowledge import KnowledgeItem


class InMemoryKnowledgeRepository(KnowledgeRepository):
    """Local in-memory knowledge store for MVP foundation."""

    def __init__(self, items: list[KnowledgeItem] | None = None) -> None:
        self._items: dict[str, KnowledgeItem] = {}
        for item in items or []:
            stored = item if item.confirmed_fields else item.with_default_confirmed_fields()
            self._items[stored.id] = stored

    async def list_all(self) -> list[KnowledgeItem]:
        return list(self._items.values())

    async def get_by_id(self, item_id: str) -> KnowledgeItem | None:
        return self._items.get(item_id)

    async def add(self, item: KnowledgeItem) -> KnowledgeItem:
        stored = item if item.confirmed_fields else item.with_default_confirmed_fields()
        self._items[stored.id] = stored
        return stored


class SqlAlchemyKnowledgeRepository(KnowledgeRepository):
    """Persist KnowledgeItem in DB.

    Uses single-table storage and stores tags/metadata/confirmed_fields as JSON.
    """

    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal

    async def list_all(self) -> list[KnowledgeItem]:
        with self._session_factory() as session:
            rows = session.scalars(select(KnowledgeItemModel).order_by(KnowledgeItemModel.created_at.desc())).all()
            return [self._to_domain(row) for row in rows]

    async def get_by_id(self, item_id: str) -> KnowledgeItem | None:
        with self._session_factory() as session:
            row = session.get(KnowledgeItemModel, item_id)
            return self._to_domain(row) if row is not None else None

    async def add(self, item: KnowledgeItem) -> KnowledgeItem:
        stored = item if item.confirmed_fields else item.with_default_confirmed_fields()
        with self._session_factory() as session:
            # Upsert by id: update existing record if it already exists.
            existing = session.get(KnowledgeItemModel, stored.id)
            model = existing or KnowledgeItemModel(id=stored.id)
            model.title = stored.title
            model.content = stored.content
            model.category = stored.category
            model.item_type = stored.item_type
            model.tags_json = json.dumps(stored.tags, ensure_ascii=False)
            model.source = stored.source
            model.confirmed_fields_json = json.dumps(sorted(stored.confirmed_fields), ensure_ascii=False)
            model.metadata_json = json.dumps(stored.metadata, ensure_ascii=False)
            session.add(model)
            session.commit()
            return stored

    def _to_domain(self, row: KnowledgeItemModel) -> KnowledgeItem:
        def _loads_json(value: str, default: Any) -> Any:
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return default

        tags = _loads_json(getattr(row, "tags_json", "[]"), [])
        confirmed = _loads_json(getattr(row, "confirmed_fields_json", "[]"), [])
        metadata = _loads_json(getattr(row, "metadata_json", "{}"), {})

        return KnowledgeItem(
            id=row.id,
            title=row.title,
            content=row.content,
            category=row.category,
            item_type=row.item_type,
            tags=[str(t) for t in tags] if isinstance(tags, list) else [],
            source=row.source,
            confirmed_fields=set(str(x) for x in confirmed) if isinstance(confirmed, list) else set(),
            metadata={str(k): str(v) for k, v in (metadata.items() if isinstance(metadata, dict) else [])},
        )
