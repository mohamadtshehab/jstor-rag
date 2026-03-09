from __future__ import annotations

import asyncio
from typing import Any

from google import genai
from groq import AsyncGroq, RateLimitError

from ..contracts.dtos import CompletionRequest, EmbeddingRequest
from ..contracts.interfaces import IAIProviderAccess
from .config_access import ConfigAccess

_MAX_RETRIES_429 = 3
_RETRY_DELAY_SECONDS = 6


class AIProviderAccess(IAIProviderAccess):
    """Uses Gemini for embeddings and Groq for generation.

    Embeddings: Gemini (google-genai). Generation: Groq (llama-3.1-8b-instant).
    """

    def __init__(self, config: ConfigAccess) -> None:
        settings = config.settings
        self._gemini = genai.Client(api_key=settings.gemini_api_key)
        self._groq = AsyncGroq(api_key=settings.groq_api_key)
        self._embedding_model = settings.embedding_model
        self._generation_model = settings.generation_model

    async def fetch_vector(self, request: EmbeddingRequest) -> list[float]:
        response = await self._gemini.aio.models.embed_content(
            model=self._embedding_model,
            contents=request.text,
        )
        embeddings = response.embeddings
        if not embeddings:
            return []
        vals = embeddings[0].values
        return list(vals) if vals is not None else []

    async def fetch_vectors_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one API call. Reduces rate limit pressure."""
        if not texts:
            return []
        response = await self._gemini.aio.models.embed_content(
            model=self._embedding_model,
            contents=texts,
        )
        embeddings = response.embeddings or []
        result: list[list[float]] = []
        for emb in embeddings:
            vals = emb.values
            result.append(list(vals) if vals is not None else [])
        return result

    async def fetch_completion(self, request: CompletionRequest) -> str:
        messages: list[dict[str, Any]] = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.append({"role": "user", "content": request.prompt})

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES_429):
            try:
                completion = await self._groq.chat.completions.create(
                    model=self._generation_model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
                return (completion.choices[0].message.content or "").strip()
            except RateLimitError as e:
                last_error = e
                if attempt < _MAX_RETRIES_429 - 1:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise
        raise last_error or RuntimeError("Unexpected retry loop exit")
