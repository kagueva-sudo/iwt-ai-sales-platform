import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.constants import ChannelType
from app.db.models import Base
from app.domain.knowledge import KnowledgeItem
from app.repositories.knowledge import SqlAlchemyKnowledgeRepository
from app.services.knowledge_loader import load_knowledge_items_from_dir, seed_knowledge_from_dir


def _session_factory(db_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


@pytest.mark.asyncio
async def test_sqlalchemy_knowledge_repository_add_and_get(tmp_path: Path) -> None:
    repo = SqlAlchemyKnowledgeRepository(session_factory=_session_factory(tmp_path / "knowledge.db"))

    item = KnowledgeItem(id="faq-1", title="Доставка", content="Доставка 2 дня.", category="faq", item_type="faq")
    # Confirmed_fields are empty by default.
    assert item.confirmed_fields == set()

    await repo.add(item)
    loaded = await repo.get_by_id("faq-1")

    assert loaded is not None
    assert loaded.id == "faq-1"
    assert loaded.title == "Доставка"
    assert loaded.content == "Доставка 2 дня."
    assert loaded.category == "faq"
    assert loaded.item_type == "faq"
    # Repository must apply confirmed_fields defaulting.
    assert loaded.confirmed_fields
    assert "content" in loaded.confirmed_fields


def test_load_knowledge_items_from_dir_maps_category_from_folder(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    (root / "delivery").mkdir(parents=True)
    (root / "delivery" / "item-1.json").write_text(
        json.dumps(
            {
                "title": "Сроки доставки",
                "content": "Доставка занимает 2 дня.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    items = load_knowledge_items_from_dir(root)
    assert len(items) == 1
    assert items[0].id == "item-1"
    assert items[0].category == "delivery"
    assert items[0].title == "Сроки доставки"


@pytest.mark.asyncio
async def test_seed_knowledge_from_dir_upserts_on_each_run(tmp_path: Path) -> None:
    db_repo = SqlAlchemyKnowledgeRepository(session_factory=_session_factory(tmp_path / "seed.db"))
    root = tmp_path / "knowledge"
    (root / "faq").mkdir(parents=True)
    faq_path = root / "faq" / "faq-1.json"
    faq_path.write_text(
        json.dumps(
            {
                "title": "Гарантия",
                "content": "Гарантия 12 месяцев.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    inserted_first = await seed_knowledge_from_dir(root, repository=db_repo)
    faq_path.write_text(
        json.dumps(
            {
                "title": "Гарантия",
                "content": "Гарантия 24 месяца.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    inserted_second = await seed_knowledge_from_dir(root, repository=db_repo)

    assert inserted_first == 1
    assert inserted_second == 1
    loaded = await db_repo.get_by_id("faq-1")
    assert loaded is not None
    assert loaded.content == "Гарантия 24 месяца."

