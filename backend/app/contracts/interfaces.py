from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel

from .dtos import (
    AIProviderConfig,
    AnswerResponse,
    ArticleData,
    ChatMessage,
    CompletionRequest,
    DocumentChunk,
    DocumentMetadata,
    EmbeddingRequest,
    IngestionResult,
    ScraperConfig,
    ServerConfig,
    StoreConfig,
    VectorSearchResult,
)


# ── Engines ──────────────────────────────────────────────────────────────────


class IParsingEngine(ABC):
    @abstractmethod
    def create_chunks(
        self, text: str, document_id: str, metadata: DocumentMetadata
    ) -> list[DocumentChunk]: ...

    @abstractmethod
    def detect_sections(self, text: str) -> list[str]: ...

    @abstractmethod
    def estimate_chunk_count(self, text: str) -> int: ...


class IGeneratingEngine(ABC):
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

    @abstractmethod
    def create_rag_system_prompt(self) -> str: ...


# ── Resource Access ──────────────────────────────────────────────────────────


class IArticleAccess(ABC):
    @abstractmethod
    async def fetch_article(self, url: str) -> ArticleData: ...

    @abstractmethod
    def validate_url(self, url: str) -> bool: ...

    @abstractmethod
    async def fetch_metadata(self, url: str) -> DocumentMetadata: ...


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
    def get_chat_model(self) -> BaseChatModel: ...

    @abstractmethod
    async def fetch_vector(self, request: EmbeddingRequest) -> list[float]: ...

    async def fetch_vectors_batch(
        self, requests: list[EmbeddingRequest]
    ) -> list[list[float]]:
        """Default: sequential fetch_vector. Implementations may override for batch API efficiency."""
        result: list[list[float]] = []
        for req in requests:
            result.append(await self.fetch_vector(req))
        return result

    @abstractmethod
    async def fetch_completion(self, request: CompletionRequest) -> str: ...


class IConfigAccess(ABC):
    @abstractmethod
    def read_ai_config(self) -> AIProviderConfig: ...

    @abstractmethod
    def read_store_config(self) -> StoreConfig: ...

    @abstractmethod
    def read_scraper_config(self) -> ScraperConfig: ...

    @abstractmethod
    def read_server_config(self) -> ServerConfig: ...


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

    @abstractmethod
    async def delete_document(self, document_id: str) -> None: ...

    @abstractmethod
    async def check_document(self, document_id: str) -> bool: ...


class IQueryManager(ABC):
    @abstractmethod
    async def query_document(
        self,
        document_id: str,
        question: str,
    ) -> AnswerResponse: ...

    @abstractmethod
    async def clear_conversation(self, document_id: str) -> None: ...

    @abstractmethod
    def get_graph_png(self) -> bytes: ...
