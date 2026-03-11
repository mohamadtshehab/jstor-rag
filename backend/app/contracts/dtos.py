from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    url: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str = ""


class ArticleData(BaseModel):
    text: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    logical_section: str
    start_offset: int
    end_offset: int
    metadata: dict = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    chunk: DocumentChunk
    score: float


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AnswerResponse(BaseModel):
    document_id: str
    thread_id: str = ""
    answer_text: str
    messages: list[ChatMessage] = Field(default_factory=list)


class IngestionResult(BaseModel):
    document_id: str
    total_chunks: int
    status: str
    article_title: str = ""


class EmbeddingRequest(BaseModel):
    text: str


class CompletionRequest(BaseModel):
    prompt: str
    temperature: float = 0.3
    max_tokens: int = 2048
    system_instruction: str = ""


class IngestPayload(BaseModel):
    url: str


class QueryPayload(BaseModel):
    document_id: str
    question: str


# ── Config group DTOs ─────────────────────────────────────────────────────────


class AIProviderConfig(BaseModel):
    gemini_api_key: str
    groq_api_key: str
    embedding_model: str
    generation_model: str


class StoreConfig(BaseModel):
    chroma_persist_dir: str


class ScraperConfig(BaseModel):
    playwright_channel: str
    playwright_state_path: str
    playwright_user_data_dir: str
    login_email: str
    login_password: str
    headless: bool = True
    do_login_flow: bool = False
    login_dialog_wait_seconds: float = 0.0


class ServerConfig(BaseModel):
    host: str
    port: int
