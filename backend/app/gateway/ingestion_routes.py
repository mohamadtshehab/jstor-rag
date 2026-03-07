from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..contracts.dtos import IngestPayload, IngestionResult
from ..dependencies import get_ingestion_manager
from ..managers.ingestion_manager import IngestionManager

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("", response_model=IngestionResult)
async def ingest_document(
    payload: IngestPayload,
    manager: IngestionManager = Depends(get_ingestion_manager),
) -> IngestionResult:
    if not payload.url.strip():
        raise HTTPException(status_code=422, detail="URL is required.")

    return await manager.ingest_document(payload.url)
