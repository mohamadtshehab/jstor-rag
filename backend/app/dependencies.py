"""Dependency injection wiring.

Factory functions consumed by FastAPI's Depends().  Each component receives
its dependencies via constructor injection, keeping the layered architecture
explicit and testable.
"""

from __future__ import annotations

from functools import lru_cache

from .engines.generation_engine import GenerationEngine
from .engines.parsing_engine import ParsingEngine
from .managers.ingestion_manager import IngestionManager
from .managers.query_manager import QueryManager
from .resource_access.ai_provider_access import AIProviderAccess
from .resource_access.article_access import ArticleAccess
from .resource_access.config_access import ConfigAccess
from .resource_access.knowledge_store_access import KnowledgeStoreAccess
from .resource_access.session_access import SessionAccess
from .utilities.notification_utility import NotificationUtility


@lru_cache
def get_config() -> ConfigAccess:
    return ConfigAccess()


@lru_cache
def get_ai_provider() -> AIProviderAccess:
    return AIProviderAccess(get_config())


@lru_cache
def get_knowledge_store() -> KnowledgeStoreAccess:
    return KnowledgeStoreAccess(get_config())


@lru_cache
def get_article_access() -> ArticleAccess:
    return ArticleAccess(config=get_config())


@lru_cache
def get_session_access() -> SessionAccess:
    return SessionAccess()


@lru_cache
def get_notification() -> NotificationUtility:
    return NotificationUtility()


@lru_cache
def get_parsing_engine() -> ParsingEngine:
    return ParsingEngine()


@lru_cache
def get_generation_engine() -> GenerationEngine:
    return GenerationEngine()


def get_ingestion_manager() -> IngestionManager:
    return IngestionManager(
        article_access=get_article_access(),
        parsing_engine=get_parsing_engine(),
        generation_engine=get_generation_engine(),
        ai_provider=get_ai_provider(),
        knowledge_store=get_knowledge_store(),
        notification=get_notification(),
    )


@lru_cache
def get_query_manager() -> QueryManager:
    return QueryManager(
        generation_engine=get_generation_engine(),
        ai_provider=get_ai_provider(),
        knowledge_store=get_knowledge_store(),
    )
