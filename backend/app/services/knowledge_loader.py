import json
from pathlib import Path

from app.domain.knowledge import KnowledgeItem
from app.repositories.knowledge import SqlAlchemyKnowledgeRepository


def load_knowledge_items_from_dir(root_dir: Path) -> list[KnowledgeItem]:
    """Load knowledge items from `knowledge/{category}/*.json` files.

    Expected JSON schema per file:
    - id (optional; defaults to filename without extension)
    - title (required)
    - content (required)
    - category (optional; defaults to folder name)
    - item_type (optional; defaults to "faq")
    - tags (optional; list[str])
    - source (optional; defaults to "knowledge_base")
    - confirmed_fields (optional; list[str])
    - metadata (optional; dict[str, str])

    Note: repository will apply confirmed_fields default rules if not provided.
    """

    items: list[KnowledgeItem] = []
    if not root_dir.exists() or not root_dir.is_dir():
        return items

    for category_dir in sorted(p for p in root_dir.iterdir() if p.is_dir()):
        category = category_dir.name
        for json_file in sorted(category_dir.glob("*.json")):
            raw = json_file.read_text(encoding="utf-8")
            payload = json.loads(raw)
            # Allow file to contain either a single object or a list of objects.
            candidates = payload if isinstance(payload, list) else [payload]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue

                item_id = str(candidate.get("id") or json_file.stem)
                title = str(candidate.get("title") or "").strip()
                content = str(candidate.get("content") or "").strip()
                if not title or not content:
                    continue

                item = KnowledgeItem(
                    id=item_id,
                    title=title,
                    content=content,
                    category=str(candidate.get("category") or category),
                    item_type=str(candidate.get("item_type") or "faq"),
                    tags=[
                        str(t)
                        for t in (candidate.get("tags") or [])
                        if str(t).strip()
                    ],
                    source=str(candidate.get("source") or "knowledge_base"),
                    confirmed_fields={
                        str(x)
                        for x in (candidate.get("confirmed_fields") or [])
                        if str(x).strip()
                    },
                    metadata={str(k): str(v) for k, v in (candidate.get("metadata") or {}).items()},
                )
                items.append(item)
    return items


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

