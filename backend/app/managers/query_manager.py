from __future__ import annotations

import hashlib

from ..contracts.dtos import AnswerResponse
from ..contracts.interfaces import (
    IAIProviderAccess,
    ICacheAccess,
    IGenerationEngine,
    IKnowledgeStoreAccess,
    IQueryManager,
)


class QueryManager(IQueryManager):
    """Orchestrates the conversational RAG query pipeline.

    Sequence: cache check → validate → embed → search → prompt → generate →
              extract citations → cache → return.
    """

    def __init__(
        self,
        generation_engine: IGenerationEngine,
        ai_provider: IAIProviderAccess,
        knowledge_store: IKnowledgeStoreAccess,
        cache: ICacheAccess,
    ) -> None:
        self._generation = generation_engine
        self._ai = ai_provider
        self._store = knowledge_store
        self._cache = cache

    async def query_document(
        self, document_id: str, question: str
    ) -> AnswerResponse:
        query_hash = self._make_hash(document_id, question)

        cached = await self._cache.get_cached_answer(query_hash)
        if cached is not None:
            return cached

        if not await self._store.exists(document_id):
            return AnswerResponse(
                document_id=document_id,
                answer_text="Document not found. Please ingest it first.",
            )

        embed_req = self._generation.create_embedding_request(question)
        query_vector = await self._ai.fetch_vector(embed_req)

        search_results = await self._store.search_similar(
            document_id, query_vector, top_k=5
        )
        if not search_results:
            return AnswerResponse(
                document_id=document_id,
                answer_text="No relevant content found for this question.",
            )

        chunks = [r.chunk for r in search_results]

        completion_req = self._generation.create_completion_request(
            question, chunks
        )
        raw_response = await self._ai.fetch_completion(completion_req)

        answer = self._generation.extract_citations(
            raw_response, chunks, document_id
        )

        await self._cache.store_answer(query_hash, answer)
        return answer

    @staticmethod
    def _make_hash(document_id: str, question: str) -> str:
        key = f"{document_id}:{question.strip().lower()}"
        return hashlib.sha256(key.encode()).hexdigest()
