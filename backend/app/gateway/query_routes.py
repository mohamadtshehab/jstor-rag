from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..contracts.dtos import AnswerResponse, QueryPayload
from ..contracts.interfaces import IQueryManager
from ..dependencies import get_query_manager

router = APIRouter(prefix="/query", tags=["Query"])


@router.get("/graph.png", response_class=Response)
async def get_graph_png(
    manager: IQueryManager = Depends(get_query_manager),
) -> Response:
    """Return a PNG visualization of the LangGraph (nodes and routes)."""
    png_bytes = manager.get_graph_png()
    return Response(content=png_bytes, media_type="image/png")


@router.post("", response_model=AnswerResponse)
async def query_document(
    payload: QueryPayload,
    manager: IQueryManager = Depends(get_query_manager),
) -> AnswerResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="Question is empty.")
    if not payload.document_id.strip():
        raise HTTPException(status_code=422, detail="document_id is required.")

    return await manager.query_document(
        payload.document_id,
        payload.question,
    )
