from __future__ import annotations

import asyncio

from google import genai
from groq import AsyncGroq, RateLimitError

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from ..contracts.dtos import CompletionRequest, EmbeddingRequest
from ..contracts.interfaces import IAIProviderAccess, IConfigUtility

_MAX_RETRIES_429 = 3
_RETRY_DELAY_SECONDS = 6


class AIProviderAccess(IAIProviderAccess):
    """Uses Gemini for embeddings and Groq for generation.

    Embeddings: Gemini (google-genai). Generation: Groq (llama-3.1-8b-instant).
    """

    def __init__(self, config: IConfigUtility) -> None:
        ai = config.read_ai_config()
        self._gemini = genai.Client(api_key=ai.gemini_api_key)
        self._groq = AsyncGroq(api_key=ai.groq_api_key)
        self._embedding_model = ai.embedding_model
        self._generation_model = ai.generation_model
        self._groq_api_key = ai.groq_api_key

    def get_chat_model(self) -> BaseChatModel:
        return ChatGroq(
            model=self._generation_model,
            api_key=self._groq_api_key,
            temperature=0,
        )

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

    async def fetch_vectors_batch(
        self, requests: list[EmbeddingRequest]
    ) -> list[list[float]]:
        """Embed multiple texts in one API call. Reduces rate limit pressure."""
        if not requests:
            return []
        response = await self._gemini.aio.models.embed_content(
            model=self._embedding_model,
            contents=[r.text for r in requests],
        )
        embeddings = response.embeddings or []
        result: list[list[float]] = []
        for emb in embeddings:
            vals = emb.values
            result.append(list(vals) if vals is not None else [])
        return result

    async def fetch_completion(self, request: CompletionRequest) -> str:
        messages: list[dict] = []
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
