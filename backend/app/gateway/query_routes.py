from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..contracts.dtos import AnswerResponse, QueryPayload
from ..contracts.interfaces import IQueryManager
from ..dependencies import get_query_manager
from ..dependencies import get_ai_provider, get_generating_engine, get_notification, get_knowledge_store
from ..contracts.interfaces import IAIProviderAccess, IGeneratingEngine, IKnowledgeStoreAccess, INotificationUtility

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


@router.post("/stream")
async def query_document_stream(
    payload: QueryPayload,
    ai_provider: IAIProviderAccess = Depends(get_ai_provider),
    generation_engine: IGeneratingEngine = Depends(get_generating_engine),
    knowledge_store: IKnowledgeStoreAccess = Depends(get_knowledge_store),
    notification: INotificationUtility = Depends(get_notification),
) -> dict:
    """Start a streaming generation for a document/question and publish deltas via websocket.

    Clients subscribed to the websocket will receive events with `event: StreamingResponse`.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="Question is empty.")
    if not payload.document_id.strip():
        raise HTTPException(status_code=422, detail="document_id is required.")

    # Build context by searching the store
    embed_req = generation_engine.create_embedding_request(payload.question)
    query_vector = await ai_provider.fetch_vector(embed_req)
    if not query_vector:
        # Unable to compute embedding for the query — notify clients and stop.
        await notification.publish(
            "StreamingResponse",
            {
                "document_id": payload.document_id,
                "delta": "[Error] Unable to compute embedding for the query.",
                "done": True,
            },
        )
        return {"status": "failed_embedding"}

    results = await knowledge_store.search_similar(payload.document_id, query_vector, top_k=5)
    # Extract non-empty context texts
    context_texts: list[str] = [r.chunk.text.strip() for r in results if (r.chunk.text or "").strip()]
    if not context_texts:
        await notification.publish(
            "StreamingResponse",
            {
                "document_id": payload.document_id,
                "delta": "[Error] No relevant context found in the document.",
                "done": True,
            },
        )
        return {"status": "no_context"}

    # Build explicit context prompt to ensure the LLM receives the retrieved text
    context_block = "\n\n---\n\n".join(f"Section: {i+1}\n{t}" for i, t in enumerate(context_texts))
    prompt = f"Context:\n{context_block}\n\nQuestion: {payload.question}\n\nAnswer:"
    completion_req = CompletionRequest(
        prompt=prompt,
        system_instruction=generation_engine.create_rag_system_prompt(),
        temperature=0.3,
        max_tokens=2048,
    )

    # Publish deltas as they arrive
    async for delta in ai_provider.fetch_completion_stream(completion_req):
        await notification.publish(
            "StreamingResponse",
            {"document_id": payload.document_id, "delta": delta, "done": False},
        )

    # Signal completion
    await notification.publish(
        "StreamingResponse",
        {"document_id": payload.document_id, "delta": "", "done": True},
    )

    return {"status": "streaming_started"}
