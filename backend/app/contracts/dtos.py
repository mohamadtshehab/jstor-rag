from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    url: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str = ""


class ArticleData(BaseModel):
    text: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class SourceLocator(BaseModel):
    chunk_id: str
    logical_section: str
    start_offset: int
    end_offset: int
    context_snippet: str


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    logical_section: str
    start_offset: int
    end_offset: int
    metadata: dict = Field(default_factory=dict)

    def to_locator(self) -> SourceLocator:
        return SourceLocator(
            chunk_id=self.chunk_id,
            logical_section=self.logical_section,
            start_offset=self.start_offset,
            end_offset=self.end_offset,
            context_snippet=self.text[:120],
        )


class VectorSearchResult(BaseModel):
    chunk: DocumentChunk
    score: float


class Citation(BaseModel):
    marker: str
    locator: SourceLocator


class AnswerResponse(BaseModel):
    document_id: str
    answer_text: str
    citations: list[Citation] = Field(default_factory=list)


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
