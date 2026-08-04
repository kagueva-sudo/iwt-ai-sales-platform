from fastapi import APIRouter, HTTPException, Query

from app.api.manager_queue_mappers import map_manager_queue_item_to_schema
from app.domain.manager_queue import ManagerQueueStatus
from app.schemas.manager_queue import ManagerQueueItemSchema, ManagerQueueStatusUpdateSchema
from app.services.composition import get_manager_queue_repository
from app.services.manager_queue_service import ManagerQueueService


router = APIRouter(prefix="/manager-queue", tags=["manager-queue"])


def _service() -> ManagerQueueService:
    return ManagerQueueService(get_manager_queue_repository())


@router.get("", response_model=list[ManagerQueueItemSchema])
async def list_manager_queue(
    status: ManagerQueueStatus | None = Query(default=None),
) -> list[ManagerQueueItemSchema]:
    items = await _service().list_items(status=status)
    return [map_manager_queue_item_to_schema(item) for item in items]


@router.get("/{request_id}", response_model=ManagerQueueItemSchema)
async def get_manager_queue_item(request_id: str) -> ManagerQueueItemSchema:
    item = await _service().get_item(request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Manager queue item not found.")
    return map_manager_queue_item_to_schema(item)


@router.patch("/{request_id}/status", response_model=ManagerQueueItemSchema)
async def update_manager_queue_status(
    request_id: str,
    payload: ManagerQueueStatusUpdateSchema,
) -> ManagerQueueItemSchema:
    item = await _service().update_status(request_id, payload.status)
    if item is None:
        raise HTTPException(status_code=404, detail="Manager queue item not found.")
    return map_manager_queue_item_to_schema(item)
