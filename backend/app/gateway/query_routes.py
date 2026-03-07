from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..contracts.dtos import AnswerResponse, QueryPayload
from ..dependencies import get_query_manager
from ..managers.query_manager import QueryManager

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=AnswerResponse)
async def query_document(
    payload: QueryPayload,
    manager: QueryManager = Depends(get_query_manager),
) -> AnswerResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="Question is empty.")
    if not payload.document_id.strip():
        raise HTTPException(status_code=422, detail="document_id is required.")

    return await manager.query_document(payload.document_id, payload.question)
