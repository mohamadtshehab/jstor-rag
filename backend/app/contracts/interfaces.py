from __future__ import annotations

from abc import ABC, abstractmethod

from .dtos import (
    AnswerResponse,
    ArticleData,
    ChatMessage,
    CompletionRequest,
    DocumentChunk,
    DocumentMetadata,
    EmbeddingRequest,
    IngestionResult,
    VectorSearchResult,
)


# ── Engines ──────────────────────────────────────────────────────────────────


class IParsingEngine(ABC):
    @abstractmethod
    def create_chunks(
        self, text: str, document_id: str, metadata: DocumentMetadata
    ) -> list[DocumentChunk]: ...


class IGenerationEngine(ABC):
    @abstractmethod
    def create_embedding_request(self, text: str) -> EmbeddingRequest: ...

    @abstractmethod
    def create_completion_request(
        self, question: str, chunks: list[DocumentChunk]
    ) -> CompletionRequest: ...

    @abstractmethod
    def create_condense_request(self, question: str, history: str) -> CompletionRequest: ...

    @abstractmethod
    def extract_citations(
        self, raw_response: str, chunks: list[DocumentChunk], document_id: str
    ) -> AnswerResponse: ...


# ── Resource Access ──────────────────────────────────────────────────────────


class IArticleAccess(ABC):
    @abstractmethod
    async def fetch_article(self, url: str) -> ArticleData: ...


class IKnowledgeStoreAccess(ABC):
    @abstractmethod
    async def store_chunks(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None: ...

    @abstractmethod
    async def search_similar(
        self, document_id: str, query_vector: list[float], top_k: int = 5
    ) -> list[VectorSearchResult]: ...

    @abstractmethod
    async def exists(self, document_id: str) -> bool: ...

    @abstractmethod
    async def delete(self, document_id: str) -> None: ...


class ISessionAccess(ABC):
    @abstractmethod
    async def create_session(
        self, session_id: str, document_id: str
    ) -> None: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> dict | None: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None: ...


class IAIProviderAccess(ABC):
    @abstractmethod
    async def fetch_vector(self, request: EmbeddingRequest) -> list[float]: ...

    async def fetch_vectors_batch(self, texts: list[str]) -> list[list[float]]:
        """Optional: embed multiple texts in one call. Default: sequential fetch_vector."""
        result: list[list[float]] = []
        for t in texts:
            req = EmbeddingRequest(text=t)
            result.append(await self.fetch_vector(req))
        return result

    @abstractmethod
    async def fetch_completion(self, request: CompletionRequest) -> str: ...


class IConfigAccess(ABC):
    @abstractmethod
    def get(self, key: str, default: str = "") -> str: ...


# ── Utilities ────────────────────────────────────────────────────────────────


class INotificationUtility(ABC):
    @abstractmethod
    async def publish(self, event: str, data: dict) -> None: ...

    @abstractmethod
    async def subscribe(self, event: str, callback: object) -> None: ...


# ── Managers ─────────────────────────────────────────────────────────────────


class IIngestionManager(ABC):
    @abstractmethod
    async def ingest_document(self, url: str) -> IngestionResult: ...


class IQueryManager(ABC):
    @abstractmethod
    async def query_document(
        self,
        document_id: str,
        question: str,
    ) -> AnswerResponse: ...
