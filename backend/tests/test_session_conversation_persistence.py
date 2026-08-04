from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.constants import ChannelType
from app.db.models import Base
from app.domain.conversations import ConversationMessage
from app.domain.sessions import SessionContext
from app.repositories.conversations import SqlAlchemyConversationRepository
from app.repositories.sessions import SqlAlchemySessionRepository
from app.services.conversation_state_service import ConversationStateService


def _session_factory(db_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


@pytest.mark.asyncio
async def test_sqlalchemy_session_get_or_create_and_save(tmp_path: Path) -> None:
    factory = _session_factory(tmp_path / "sessions.db")
    repo = SqlAlchemySessionRepository(session_factory=factory)

    first = await repo.get_or_create("client-1", ChannelType.MAX.value)
    second = await repo.get_or_create("client-1", ChannelType.MAX.value)

    assert first.session_id == second.session_id
    assert first.dialog_id == second.dialog_id
    assert first.channel == ChannelType.MAX

    first.metadata["note"] = "kept"
    await repo.save(first)
    reloaded = await repo.get_or_create("client-1", ChannelType.MAX.value)
    assert reloaded.metadata["note"] == "kept"


@pytest.mark.asyncio
async def test_session_survives_repository_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "sessions_restart.db"
    repo1 = SqlAlchemySessionRepository(session_factory=_session_factory(db_path))
    created = await repo1.get_or_create("client-restart", ChannelType.EMAIL.value)

    repo2 = SqlAlchemySessionRepository(session_factory=_session_factory(db_path))
    loaded = await repo2.get_or_create("client-restart", ChannelType.EMAIL.value)

    assert loaded.session_id == created.session_id
    assert loaded.dialog_id == created.dialog_id
    assert loaded.channel == ChannelType.EMAIL


@pytest.mark.asyncio
async def test_sqlalchemy_conversation_messages_persist(tmp_path: Path) -> None:
    factory = _session_factory(tmp_path / "conversations.db")
    repo = SqlAlchemyConversationRepository(session_factory=factory)

    await repo.add_message(
        "dialog-1",
        ConversationMessage(role="user", text="Какая цена?", message_id="m-1"),
    )
    await repo.add_message(
        "dialog-1",
        ConversationMessage(role="assistant", text="Уточню у менеджера."),
    )

    context = await repo.get_context("dialog-1")
    assert context.conversation_id == "dialog-1"
    assert len(context.recent_messages) == 2
    assert context.recent_messages[0].text == "Какая цена?"
    assert context.recent_messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_conversation_keeps_only_last_20_messages(tmp_path: Path) -> None:
    factory = _session_factory(tmp_path / "conversations_trim.db")
    repo = SqlAlchemyConversationRepository(session_factory=factory)

    for index in range(25):
        await repo.add_message(
            "dialog-trim",
            ConversationMessage(role="user", text=f"msg-{index}"),
        )

    context = await repo.get_context("dialog-trim")
    assert len(context.recent_messages) == 20
    assert context.recent_messages[0].text == "msg-5"
    assert context.recent_messages[-1].text == "msg-24"


@pytest.mark.asyncio
async def test_conversation_survives_repository_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "conversations_restart.db"
    repo1 = SqlAlchemyConversationRepository(session_factory=_session_factory(db_path))
    await repo1.add_message(
        "dialog-restart",
        ConversationMessage(role="user", text="Нужна цена насоса"),
    )

    repo2 = SqlAlchemyConversationRepository(session_factory=_session_factory(db_path))
    context = await repo2.get_context("dialog-restart")

    assert len(context.recent_messages) == 1
    assert context.recent_messages[0].text == "Нужна цена насоса"


@pytest.mark.asyncio
async def test_conversation_state_service_uses_sql_repositories(tmp_path: Path) -> None:
    factory = _session_factory(tmp_path / "state_service.db")
    service = ConversationStateService(
        session_repository=SqlAlchemySessionRepository(session_factory=factory),
        conversation_repository=SqlAlchemyConversationRepository(session_factory=factory),
    )

    session = await service.get_or_create_session("c-42", ChannelType.WEBSITE_CHAT)
    await service.append_message(
        session.dialog_id,
        ConversationMessage(role="user", text="Привет"),
    )
    context = await service.load_context(session.dialog_id)

    assert isinstance(session, SessionContext)
    assert context.recent_messages[0].text == "Привет"


def test_ai_core_does_not_know_session_conversation_persistence() -> None:
    import app.ai_core.core as core_module

    source = open(core_module.__file__, encoding="utf-8").read()
    assert "SqlAlchemySessionRepository" not in source
    assert "SqlAlchemyConversationRepository" not in source
    assert "SessionModel" not in source
    assert "conversation_messages" not in source
