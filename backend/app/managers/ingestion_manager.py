from __future__ import annotations

import asyncio
import uuid

from ..contracts.dtos import IngestionResult
from ..contracts.interfaces import (
    IArticleAccess,
    IAIProviderAccess,
    IGenerationEngine,
    IIngestionManager,
    IKnowledgeStoreAccess,
    INotificationUtility,
    IParsingEngine,
)


class IngestionManager(IIngestionManager):
    """Orchestrates the document ingestion pipeline.

    Sequence: fetch (via ArticleAccess) → parse → embed → store → notify.
    Client provides only the URL; all data fetching is delegated to ArticleAccess.
    """

    def __init__(
        self,
        article_access: IArticleAccess,
        parsing_engine: IParsingEngine,
        generation_engine: IGenerationEngine,
        ai_provider: IAIProviderAccess,
        knowledge_store: IKnowledgeStoreAccess,
        notification: INotificationUtility,
    ) -> None:
        self._article = article_access
        self._parsing = parsing_engine
        self._generation = generation_engine
        self._ai = ai_provider
        self._store = knowledge_store
        self._notify = notification

    async def ingest_document(self, url: str) -> IngestionResult:
        article = await self._article.fetch_article(url)
        document_id = str(uuid.uuid4())

        chunks = self._parsing.create_chunks(
            article.text, document_id, article.metadata
        )
        if not chunks:
            return IngestionResult(
                document_id=document_id,
                total_chunks=0,
                status="empty",
                article_title=article.metadata.title,
            )

        texts = [
            self._generation.create_embedding_request(c.text).text
            for c in chunks
        ]
        batch_size = 20
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            if i > 0:
                await asyncio.sleep(1.0)
            batch = texts[i : i + batch_size]
            batch_vecs = await self._ai.fetch_vectors_batch(batch)
            vectors.extend(batch_vecs)

        await self._store.store_chunks(document_id, chunks, vectors)

        await self._notify.publish(
            "DocumentReady",
            {"document_id": document_id, "total_chunks": len(chunks)},
        )

        return IngestionResult(
            document_id=document_id,
            total_chunks=len(chunks),
            status="ready",
            article_title=article.metadata.title,
        )
