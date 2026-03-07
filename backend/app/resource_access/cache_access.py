from __future__ import annotations

import time

from ..contracts.dtos import AnswerResponse
from ..contracts.interfaces import ICacheAccess


class CacheAccess(ICacheAccess):
    """In-memory answer cache with TTL.

    Hides the caching mechanism.  Can be swapped for Redis or another store
    without touching any other component.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._store: dict[str, tuple[AnswerResponse, float]] = {}
        self._ttl = ttl_seconds

    async def get_cached_answer(self, query_hash: str) -> AnswerResponse | None:
        entry = self._store.get(query_hash)
        if entry is None:
            return None
        answer, ts = entry
        if time.time() - ts > self._ttl:
            del self._store[query_hash]
            return None
        return answer

    async def store_answer(
        self, query_hash: str, answer: AnswerResponse
    ) -> None:
        self._store[query_hash] = (answer, time.time())

    def invalidate_document(self, document_id: str) -> None:
        keys_to_remove = [
            k
            for k, (ans, _) in self._store.items()
            if ans.document_id == document_id
        ]
        for k in keys_to_remove:
            del self._store[k]
