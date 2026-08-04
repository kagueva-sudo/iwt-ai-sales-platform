from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.constants import ChannelType, HandoffReason
from app.db.models import Base
from app.domain.manager_queue import ManagerQueueItem, ManagerQueueStatus
from app.repositories.manager_queue import SqlAlchemyManagerQueueRepository


def _build_file_repo(db_path: Path) -> SqlAlchemyManagerQueueRepository:
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    return SqlAlchemyManagerQueueRepository(session_factory=sessionmaker(bind=engine))


@pytest.mark.asyncio
async def test_sqlalchemy_manager_queue_crud(tmp_path: Path) -> None:
    repo = _build_file_repo(tmp_path / "manager_queue.db")
    item = ManagerQueueItem(
        request_id="req-persist-1",
        channel=ChannelType.MAX,
        customer_name="Иван",
        customer_contact="+79990001122",
        conversation_history=["Какая цена?"],
        ai_response="Нужна консультация",
        handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
    )

    await repo.add(item)
    loaded = await repo.get("req-persist-1")

    assert loaded is not None
    assert loaded.customer_name == "Иван"
    assert loaded.conversation_history == ["Какая цена?"]
    assert loaded.status == ManagerQueueStatus.NEW

    updated = await repo.update_status("req-persist-1", ManagerQueueStatus.IN_PROGRESS)
    assert updated is not None
    assert updated.status == ManagerQueueStatus.IN_PROGRESS

    by_status = await repo.list_by_status(ManagerQueueStatus.IN_PROGRESS)
    assert len(by_status) == 1
    assert by_status[0].request_id == "req-persist-1"


@pytest.mark.asyncio
async def test_manager_queue_survives_repository_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "manager_queue_restart.db"
    item = ManagerQueueItem(
        request_id="req-restart-1",
        channel=ChannelType.EMAIL,
        customer_name=None,
        customer_contact="client@example.com",
        conversation_history=["Subject: Цена", "Нужна цена"],
        ai_response="Передам менеджеру",
        handoff_reason=HandoffReason.NO_CONFIRMED_DATA,
        status=ManagerQueueStatus.NEW,
    )

    repo1 = _build_file_repo(db_path)
    await repo1.add(item)

    # Simulate process restart: new engine/session factory against the same DB file.
    repo2 = _build_file_repo(db_path)
    loaded = await repo2.get("req-restart-1")

    assert loaded is not None
    assert loaded.channel == ChannelType.EMAIL
    assert loaded.customer_contact == "client@example.com"
    assert loaded.conversation_history == ["Subject: Цена", "Нужна цена"]
    assert loaded.ai_response == "Передам менеджеру"
    assert loaded.handoff_reason == HandoffReason.NO_CONFIRMED_DATA


def test_ai_core_does_not_know_sqlalchemy_manager_queue() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "SqlAlchemyManagerQueueRepository" not in source
    assert "ManagerQueueModel" not in source
    assert "manager_queue" not in source
