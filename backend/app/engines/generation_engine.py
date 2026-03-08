from __future__ import annotations

from ..contracts.dtos import (
    AnswerResponse,
    CompletionRequest,
    DocumentChunk,
    EmbeddingRequest,
)
from ..contracts.interfaces import IGenerationEngine

_SYSTEM_PROMPT = """\
You are a research assistant analysing an academic article.
Answer the question using ONLY the provided context chunks.
If the context does not contain enough information, say so explicitly.
Do NOT fabricate information."""


class GenerationEngine(IGenerationEngine):
    """Pure business logic for AI interactions.

    Produces domain-level intermediate representations (EmbeddingRequest,
    CompletionRequest).  Knows nothing about Gemini, OpenAI, or any
    provider-specific payload format.
    """

    def create_embedding_request(self, text: str) -> EmbeddingRequest:
        cleaned = " ".join(text.split())
        return EmbeddingRequest(text=cleaned)

    def create_completion_request(
        self, question: str, chunks: list[DocumentChunk]
    ) -> CompletionRequest:
        context_parts: list[str] = []
        for chunk in chunks:
            header = f"Section: {chunk.logical_section}"
            context_parts.append(f"{header}\n{chunk.text}")

        context_block = "\n\n---\n\n".join(context_parts)
        prompt = f"Context:\n{context_block}\n\nQuestion: {question}\n\nAnswer:"

        return CompletionRequest(
            prompt=prompt,
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
        )

    def create_condense_request(self, question: str, history: str) -> CompletionRequest:
        prompt = (
            f"Given the conversation history:\n{history}\n\n"
            f"And the follow-up question: {question}\n\n"
            "Rephrase the follow-up question to be a standalone search query. "
            "Do not answer the question, just rewrite it for semantic search."
        )
        return CompletionRequest(
            prompt=prompt,
            temperature=0.1,
            max_tokens=256,
        )

    def extract_citations(
        self, raw_response: str, chunks: list[DocumentChunk], document_id: str
    ) -> AnswerResponse:
        return AnswerResponse(
            document_id=document_id,
            answer_text=raw_response.strip(),
        )
