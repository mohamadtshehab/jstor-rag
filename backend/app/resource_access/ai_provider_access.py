from __future__ import annotations

from google import genai
from google.genai import types

from ..contracts.dtos import CompletionRequest, EmbeddingRequest
from ..contracts.interfaces import IAIProviderAccess
from .config_access import ConfigAccess


class AIProviderAccess(IAIProviderAccess):
    """Translates domain-level AI requests into Gemini-specific payloads.

    Swapping providers (OpenAI, Anthropic, …) only requires replacing this
    component — Engines never see provider-specific formats.
    """

    def __init__(self, config: ConfigAccess) -> None:
        settings = config.settings
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._embedding_model = settings.embedding_model
        self._generation_model = settings.generation_model

    async def fetch_vector(self, request: EmbeddingRequest) -> list[float]:
        response = await self._client.aio.models.embed_content(
            model=self._embedding_model,
            contents=request.text,
        )
        return list(response.embeddings[0].values)

    async def fetch_completion(self, request: CompletionRequest) -> str:
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )
        if request.system_instruction:
            config.system_instruction = request.system_instruction

        response = await self._client.aio.models.generate_content(
            model=self._generation_model,
            contents=request.prompt,
            config=config,
        )
        return response.text or ""
