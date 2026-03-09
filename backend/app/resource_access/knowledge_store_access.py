from __future__ import annotations

import chromadb

from ..contracts.dtos import DocumentChunk, VectorSearchResult
from ..contracts.interfaces import IConfigAccess, IKnowledgeStoreAccess

_COLLECTION = "jstor_chunks"


class KnowledgeStoreAccess(IKnowledgeStoreAccess):
    """Hides ChromaDB behind atomic domain operations.

    All vector math, storage format, and collection management is encapsulated
    here.  The rest of the system sees only StoreChunks / SearchSimilar / Exists.
    """

    def __init__(self, config: IConfigAccess) -> None:
        persist_dir = config.read_store_config().chroma_persist_dir
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    async def store_chunks(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors,  # type: ignore[arg-type]
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "document_id": document_id,
                    "logical_section": c.logical_section,
                    "start_offset": c.start_offset,
                    "end_offset": c.end_offset,
                    "chunk_id": c.chunk_id,
                }
                for c in chunks
            ],
        )

    async def search_similar(
        self, document_id: str, query_vector: list[float], top_k: int = 1
    ) -> list[VectorSearchResult]:
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={"document_id": document_id},
            include=["documents", "metadatas", "distances"],
        )

        out: list[VectorSearchResult] = []
        if not results["ids"] or not results["ids"][0]:
            return out

        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]  # type: ignore[index]
            text = results["documents"][0][i]  # type: ignore[index]
            distance = results["distances"][0][i]  # type: ignore[index]

            so = meta.get("start_offset")
            eo = meta.get("end_offset")
            chunk = DocumentChunk(
                chunk_id=str(chunk_id),
                document_id=document_id,
                text=str(text) if text is not None else "",
                logical_section=str(meta.get("logical_section") or ""),
                start_offset=int(so) if isinstance(so, (int, float)) else 0,
                end_offset=int(eo) if isinstance(eo, (int, float)) else 0,
            )
            out.append(VectorSearchResult(chunk=chunk, score=1.0 - distance))
        return out

    async def exists(self, document_id: str) -> bool:
        results = self._collection.get(
            where={"document_id": document_id},
            limit=1,
            include=[],
        )
        return bool(results["ids"])

    async def delete(self, document_id: str) -> None:
        ids = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )["ids"]
        if ids:
            self._collection.delete(ids=ids)
