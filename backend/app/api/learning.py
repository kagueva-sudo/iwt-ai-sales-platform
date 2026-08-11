from fastapi import APIRouter, HTTPException, Query

from app.core.errors import ProviderError
from app.learning.models import KnowledgeCandidate, KnowledgeCandidateStatus
from app.learning.schemas import CandidateReviewSchema, KnowledgeCandidateSchema
from app.services.composition import get_candidate_service


router = APIRouter(prefix="/learning", tags=["learning"])


def _to_schema(candidate: KnowledgeCandidate) -> KnowledgeCandidateSchema:
    return KnowledgeCandidateSchema(
        id=candidate.id,
        conversation_id=candidate.conversation_id,
        question=candidate.question,
        ai_answer=candidate.ai_answer,
        manager_answer=candidate.manager_answer,
        source_refs=list(candidate.source_refs),
        intent=candidate.intent,
        reason=candidate.reason,
        status=candidate.status,
        created_at=candidate.created_at,
        reviewed_at=candidate.reviewed_at,
        reviewed_by=candidate.reviewed_by,
        published_knowledge_id=candidate.published_knowledge_id,
        kb_version=candidate.kb_version,
    )


@router.get("/candidates", response_model=list[KnowledgeCandidateSchema])
async def list_candidates(
    status: KnowledgeCandidateStatus | None = Query(default=None),
) -> list[KnowledgeCandidateSchema]:
    items = await get_candidate_service().list_candidates(status=status)
    return [_to_schema(item) for item in items]


@router.get("/candidates/{candidate_id}", response_model=KnowledgeCandidateSchema)
async def get_candidate(candidate_id: str) -> KnowledgeCandidateSchema:
    item = await get_candidate_service().get_candidate(candidate_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge candidate not found.")
    return _to_schema(item)


@router.post("/candidates/{candidate_id}/approve", response_model=KnowledgeCandidateSchema)
async def approve_candidate(
    candidate_id: str,
    payload: CandidateReviewSchema,
) -> KnowledgeCandidateSchema:
    try:
        item = await get_candidate_service().approve(
            candidate_id,
            reviewed_by=payload.reviewed_by,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_schema(item)


@router.post("/candidates/{candidate_id}/reject", response_model=KnowledgeCandidateSchema)
async def reject_candidate(
    candidate_id: str,
    payload: CandidateReviewSchema,
) -> KnowledgeCandidateSchema:
    try:
        item = await get_candidate_service().reject(
            candidate_id,
            reviewed_by=payload.reviewed_by,
            reason=payload.reason,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_schema(item)
