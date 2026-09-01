import unittest

from app.contracts.dtos import DocumentMetadata
from app.managers.ingestion_manager import IngestionManager


class _FakeArticleAccess:
    async def fetch_article(self, url):
        raise AssertionError(f"fetch_article should not be called for test text ingestion: {url!r}")

    def validate_url(self, url):
        return False

    async def fetch_metadata(self, url):
        return DocumentMetadata(url=url)


class _FakeAIProvider:
    async def fetch_vectors_batch(self, requests):
        return [[0.1, 0.2, 0.3] for _ in requests]


class _FakeKnowledgeStore:
    async def store_chunks(self, document_id, chunks, vectors):
        self.document_id = document_id
        self.chunks = chunks
        self.vectors = vectors

    async def delete(self, document_id):
        pass

    async def exists(self, document_id):
        return False


class _FakeNotification:
    async def publish(self, event, data):
        self.event = event
        self.data = data

    async def subscribe(self, event, callback):
        pass


class TestTestTextIngestion(unittest.IsolatedAsyncioTestCase):
    async def test_ingest_document_uses_example_text_when_url_is_empty(self):
        manager = IngestionManager(
            article_access=_FakeArticleAccess(),
            parsing_engine=None,
            generation_engine=None,
            ai_provider=_FakeAIProvider(),
            knowledge_store=_FakeKnowledgeStore(),
            notification=_FakeNotification(),
        )

        manager._parsing = __import__("app.engines.parsing_engine", fromlist=["ParsingEngine"]).ParsingEngine()
        manager._generation = __import__("app.engines.generating_engine", fromlist=["GeneratingEngine"]).GeneratingEngine()

        result = await manager.ingest_document("")

        self.assertEqual(result.status, "ready")
        self.assertGreater(result.total_chunks, 0)
        self.assertIn("The Case of the Colorblind Painter", result.article_title)


if __name__ == "__main__":
    unittest.main()
