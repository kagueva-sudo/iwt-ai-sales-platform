import json
from pathlib import Path

from app.domain.knowledge import KnowledgeItem
from app.repositories.knowledge import SqlAlchemyKnowledgeRepository


def _parse_item(candidate: dict, *, default_id: str, default_category: str) -> KnowledgeItem | None:
    title = str(candidate.get("title") or "").strip()
    content = str(candidate.get("content") or "").strip()
    if not title or not content:
        return None

    return KnowledgeItem(
        id=str(candidate.get("id") or default_id),
        title=title,
        content=content,
        category=str(candidate.get("category") or default_category),
        item_type=str(candidate.get("item_type") or "faq"),
        tags=[str(t) for t in (candidate.get("tags") or []) if str(t).strip()],
        source=str(candidate.get("source") or "knowledge_base"),
        confirmed_fields={
            str(x) for x in (candidate.get("confirmed_fields") or []) if str(x).strip()
        },
        metadata={str(k): str(v) for k, v in (candidate.get("metadata") or {}).items()},
    )


def _load_json_file(json_file: Path, *, default_category: str) -> list[KnowledgeItem]:
    raw = json_file.read_text(encoding="utf-8")
    payload = json.loads(raw)
    candidates = payload if isinstance(payload, list) else [payload]
    items: list[KnowledgeItem] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        default_id = json_file.stem if len(candidates) == 1 else f"{json_file.stem}-{index + 1}"
        item = _parse_item(candidate, default_id=default_id, default_category=default_category)
        if item is not None:
            items.append(item)
    return items


def load_knowledge_items_from_dir(root_dir: Path) -> list[KnowledgeItem]:
    """Load knowledge items from domain JSON files.

    Supported layouts:
    1) Preferred: `knowledge/{domain}.json` — array (or one object) of items.
       Category defaults to the filename stem (`delivery`, `payment`, ...).
    2) Legacy: `knowledge/{category}/*.json` — still supported for tests/migration.

    Item schema:
    - id (optional)
    - title (required)
    - content (required)
    - category / item_type / tags / source / confirmed_fields / metadata (optional)
    """

    items: list[KnowledgeItem] = []
    if not root_dir.exists() or not root_dir.is_dir():
        return items

    # Domain files at knowledge root: company.json, delivery.json, ...
    for json_file in sorted(root_dir.glob("*.json")):
        items.extend(_load_json_file(json_file, default_category=json_file.stem))

    # Legacy folder layout: knowledge/{category}/*.json
    for category_dir in sorted(p for p in root_dir.iterdir() if p.is_dir()):
        category = category_dir.name
        for json_file in sorted(category_dir.glob("*.json")):
            items.extend(_load_json_file(json_file, default_category=category))

    # Prefer first occurrence when the same id exists in both layouts.
    unique: dict[str, KnowledgeItem] = {}
    for item in items:
        unique.setdefault(item.id, item)
    return list(unique.values())


async def seed_knowledge_from_dir(
    root_dir: Path,
    *,
    repository: SqlAlchemyKnowledgeRepository | None = None,
) -> int:
    """Seed persisted knowledge from filesystem.

    Upserts all items from JSON files by id and removes DB items
    that are no longer present in the knowledge directory.
    """
    repo = repository or SqlAlchemyKnowledgeRepository()
    items = load_knowledge_items_from_dir(root_dir)
    loaded_ids = {item.id for item in items}
    upserted = 0
    for item in items:
        stored = await repo.add(item)
        if stored is not None:
            upserted += 1

    for existing in await repo.list_all():
        if existing.id not in loaded_ids:
            await repo.delete(existing.id)

    return upserted


def default_knowledge_dir() -> Path:
    # backend/app/services/knowledge_loader.py → project_root/knowledge
    return Path(__file__).resolve().parents[3] / "knowledge"
