from __future__ import annotations

import re

from ..contracts.dtos import (
    AnswerResponse,
    Citation,
    CompletionRequest,
    DocumentChunk,
    EmbeddingRequest,
)
from ..contracts.interfaces import IGenerationEngine

_SYSTEM_PROMPT = """\
You are a research assistant analysing an academic article.
Answer the question using ONLY the provided context chunks.
Cite every claim using bracketed numbers like [1], [2], etc., corresponding
to the chunk indices in the context below.
If the context does not contain enough information, say so explicitly.
Do NOT fabricate information."""

_CITATION_RE = re.compile(r"\[(\d+)\]")


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
        for i, chunk in enumerate(chunks):
            header = f"[{i + 1}] Section: {chunk.logical_section}"
            context_parts.append(f"{header}\n{chunk.text}")

        context_block = "\n\n---\n\n".join(context_parts)
        prompt = (
            f"Context:\n{context_block}\n\n"
            f"Question: {question}\n\n"
            "Answer (with citations):"
        )

        return CompletionRequest(
            prompt=prompt,
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
        )

    def extract_citations(
        self, raw_response: str, chunks: list[DocumentChunk], document_id: str
    ) -> AnswerResponse:
        markers = _CITATION_RE.findall(raw_response)
        seen: set[int] = set()
        citations: list[Citation] = []

        for marker_str in markers:
            idx = int(marker_str) - 1
            if idx in seen or idx < 0 or idx >= len(chunks):
                continue
            seen.add(idx)
            citations.append(
                Citation(
                    marker=f"[{marker_str}]",
                    locator=chunks[idx].to_locator(),
                )
            )

        return AnswerResponse(
            document_id=document_id,
            answer_text=raw_response.strip(),
            citations=citations,
        )
