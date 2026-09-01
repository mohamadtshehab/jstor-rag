from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from ..contracts.dtos import ArticleData, DocumentMetadata, IngestionResult
from ..contracts.interfaces import (
    IArticleAccess,
    IAIProviderAccess,
    IGeneratingEngine,
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
        generation_engine: IGeneratingEngine,
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
        article = await self._load_ingestion_source(url)
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

        embed_requests = [
            self._generation.create_embedding_request(c.text) for c in chunks
        ]
        batch_size = 20
        vectors: list[list[float]] = []
        for i in range(0, len(embed_requests), batch_size):
            if i > 0:
                await asyncio.sleep(1.0)
            batch_vecs = await self._ai.fetch_vectors_batch(
                embed_requests[i : i + batch_size]
            )
            vectors.extend(batch_vecs)

        # Filter out any chunks with empty embeddings (some providers may return
        # empty arrays for certain inputs). Chroma requires non-empty embeddings.
        filtered_chunks: list[DocumentChunk] = []
        filtered_vectors: list[list[float]] = []
        for chunk, vec in zip(chunks, vectors):
            if vec:
                filtered_chunks.append(chunk)
                filtered_vectors.append(vec)

        if not filtered_chunks:
            # Nothing to store — return an 'empty' ingestion result.
            await self._notify.publish(
                "DocumentReady",
                {"document_id": document_id, "total_chunks": 0},
            )
            return IngestionResult(
                document_id=document_id,
                total_chunks=0,
                status="empty",
                article_title=article.metadata.title,
            )

        await self._store.store_chunks(document_id, filtered_chunks, filtered_vectors)

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

    async def _load_ingestion_source(self, url: str) -> ArticleData:
        if not url.strip() or url.strip().lower() in {"test", "example", "example_text", "example_text.txt"}:
            example_path = Path(__file__).resolve().parents[3] / "example_text.txt"
            if example_path.exists():
                return ArticleData(
                    text=example_path.read_text(encoding="utf-8"),
                    metadata=DocumentMetadata(
                        url="test-text",
                        title="The Case of the Colorblind Painter",
                    ),
                )

        return await self._article.fetch_article(url)

    async def delete_document(self, document_id: str) -> None:
        await self._store.delete(document_id)

    async def check_document(self, document_id: str) -> bool:
        return await self._store.exists(document_id)
