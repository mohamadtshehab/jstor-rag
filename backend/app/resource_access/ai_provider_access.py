from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from langchain_core.messages import AIMessage

from ..contracts.dtos import CompletionRequest, EmbeddingRequest
from ..contracts.interfaces import IAIProviderAccess, IConfigUtility


class _OllamaChatModel:
    """Lightweight adapter that exposes `bind_tools` and `ainvoke` used by the QueryManager.

    This adapter simply forwards prompts to the provider's `fetch_completion` and
    returns an `AIMessage` containing the generated text. It intentionally does not
    implement full tool-call mediation — tools will be available on the wrapper but
    the LLM won't automatically invoke them.
    """

    def __init__(self, provider: "AIProviderAccess") -> None:
        self._provider = provider
        self._tools = []

    def bind_tools(self, tools: list[Any], tool_choice: str = "auto") -> "_OllamaChatModel":
        self._tools = tools
        return self

    async def ainvoke(self, messages: list[Any], config: Any) -> AIMessage:
        parts: list[str] = []
        for m in messages:
            content = getattr(m, "content", None)
            if content is not None:
                parts.append(str(content))
        prompt = "\n\n".join(parts)
        req = CompletionRequest(prompt=prompt, temperature=0.0, max_tokens=1024)
        text = await self._provider.fetch_completion(req)
        return AIMessage(content=text)


class AIProviderAccess(IAIProviderAccess):
    """Uses Ollama for both generation and embeddings via the local HTTP API.

    Generation model: `phi` (by default)
    Embedding model: `nomic embed text` (by default)
    """

    def __init__(self, config: IConfigUtility) -> None:
        ai = config.read_ai_config()
        self._embedding_model = ai.embedding_model
        self._generation_model = ai.generation_model
        self._ollama_api_base = ai.ollama_api_base or "http://localhost:11434"
        self._ollama_api_key = ai.ollama_api_key or ""
        self._client = httpx.AsyncClient(base_url=self._ollama_api_base, timeout=30.0)
        self._logger = logging.getLogger(__name__)

    def get_chat_model(self) -> _OllamaChatModel:
        return _OllamaChatModel(self)

    async def _post(self, path: str, payload: dict) -> Any:
        headers: dict[str, str] = {}
        if self._ollama_api_key:
            headers["Authorization"] = f"Bearer {self._ollama_api_key}"
        resp = await self._client.post(path, json=payload, headers=headers)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text

    async def fetch_vector(self, request: EmbeddingRequest) -> list[float]:
        payload = {"model": self._embedding_model, "input": request.text}
        data = await self._post("/api/embed", payload)
        # Accept several possible response shapes to be resilient across Ollama versions
        emb: list[float] = []
        if isinstance(data, dict):
            if "embeddings" in data and data["embeddings"]:
                first = data["embeddings"][0]
                if isinstance(first, dict):
                    emb = first.get("embedding") or first.get("values") or []
                else:
                    emb = list(first)
            elif "data" in data and isinstance(data["data"], list) and data["data"]:
                maybe = data["data"][0]
                if isinstance(maybe, dict):
                    emb = maybe.get("embedding") or maybe.get("values") or []
            elif "embedding" in data and isinstance(data["embedding"], list):
                emb = data["embedding"]
            if not emb:
                # Retry using 'prompt' as some Ollama models expect that field name.
                try:
                    alt_payload = {"model": self._embedding_model, "prompt": request.text}
                    alt_data = await self._post("/api/embed", alt_payload)
                    # attempt extraction from alt_data
                    alt_emb: list[float] = []
                    if isinstance(alt_data, dict):
                        if "embeddings" in alt_data and alt_data["embeddings"]:
                            first = alt_data["embeddings"][0]
                            if isinstance(first, dict):
                                alt_emb = first.get("embedding") or first.get("values") or []
                            else:
                                alt_emb = list(first)
                        elif "data" in alt_data and isinstance(alt_data["data"], list) and alt_data["data"]:
                            maybe = alt_data["data"][0]
                            if isinstance(maybe, dict):
                                alt_emb = maybe.get("embedding") or maybe.get("values") or []
                        elif "embedding" in alt_data and isinstance(alt_data["embedding"], list):
                            alt_emb = alt_data["embedding"]

                    if alt_emb:
                        return list(alt_emb)
                except Exception:
                    pass

                try:
                    self._logger.warning("Empty embedding returned from Ollama; payload=%s response=%s", payload, data)
                except Exception:
                    pass
            return list(emb) if emb else []

    async def fetch_vectors_batch(self, requests: list[EmbeddingRequest]) -> list[list[float]]:
        if not requests:
            return []
        payload = {"model": self._embedding_model, "input": [r.text for r in requests]}
        data = await self._post("/api/embed", payload)
        out: list[list[float]] = []
        if isinstance(data, dict):
            if "embeddings" in data:
                for e in data["embeddings"]:
                    if isinstance(e, dict):
                        vals = e.get("embedding") or e.get("values") or []
                    else:
                        vals = list(e)
                    out.append(list(vals))
                return out
            if "data" in data:
                for item in data["data"]:
                    if isinstance(item, dict):
                        vals = item.get("embedding") or item.get("values") or []
                    else:
                        vals = list(item)
                    out.append(list(vals))
                return out
            if not out:
                # Retry with 'prompt' as key for batch requests
                try:
                    alt_payload = {"model": self._embedding_model, "prompt": [r.text for r in requests]}
                    alt_data = await self._post("/api/embed", alt_payload)
                    if isinstance(alt_data, dict):
                        if "embeddings" in alt_data:
                            for e in alt_data["embeddings"]:
                                if isinstance(e, dict):
                                    vals = e.get("embedding") or e.get("values") or []
                                else:
                                    vals = list(e)
                                out.append(list(vals))
                        elif "data" in alt_data:
                            for item in alt_data["data"]:
                                if isinstance(item, dict):
                                    vals = item.get("embedding") or item.get("values") or []
                                else:
                                    vals = list(item)
                                out.append(list(vals))
                    if out:
                        return out
                except Exception:
                    pass

                try:
                    self._logger.warning("Empty embeddings batch response from Ollama; payload=%s response=%s", payload, data)
                except Exception:
                    pass
            return out

    async def fetch_completion(self, request: CompletionRequest) -> str:
        payload = {
            "model": self._generation_model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        # Ollama's /api/generate may stream or return JSON/text; handle both.
        headers: dict[str, str] = {}
        if self._ollama_api_key:
            headers["Authorization"] = f"Bearer {self._ollama_api_key}"
        resp = await self._client.post("/api/generate", json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception:
            return resp.text

        # Best-effort extraction of text from common shapes
        if isinstance(data, dict):
            if "text" in data and isinstance(data["text"], str):
                return data["text"].strip()
            if "content" in data and isinstance(data["content"], str):
                return data["content"].strip()
            if "output" in data and isinstance(data["output"], str):
                return data["output"].strip()
            if "results" in data and isinstance(data["results"], list) and data["results"]:
                first = data["results"][0]
                if isinstance(first, dict):
                    for k in ("content", "text", "output"):
                        if k in first and isinstance(first[k], str):
                            return first[k].strip()
                else:
                    return str(first).strip()
        return str(data).strip()

    async def fetch_completion_stream(self, request: CompletionRequest):
        """Async generator yielding incremental text chunks from Ollama's streaming API."""
        payload = {
            "model": self._generation_model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        headers: dict[str, str] = {}
        if self._ollama_api_key:
            headers["Authorization"] = f"Bearer {self._ollama_api_key}"

        async with self._client.stream("POST", "/api/generate", json=payload, headers=headers, timeout=httpx.Timeout(None)) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_text():
                if not chunk:
                    continue
                # Ollama may stream JSON lines or plain text; attempt to extract any text fields.
                text = chunk
                # Try parse JSON snippets
                try:
                    import json as _json

                    parsed = _json.loads(chunk)
                    if isinstance(parsed, dict):
                        for k in ("text", "content", "output"):
                            if k in parsed and isinstance(parsed[k], str):
                                text = parsed[k]
                                break
                        else:
                            # If it's a results array
                            if "results" in parsed and parsed["results"]:
                                first = parsed["results"][0]
                                if isinstance(first, dict):
                                    for k in ("content", "text", "output"):
                                        if k in first and isinstance(first[k], str):
                                            text = first[k]
                                            break
                except Exception:
                    pass

                yield text
