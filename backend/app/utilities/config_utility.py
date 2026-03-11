from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

from ..contracts.dtos import AIProviderConfig, ScraperConfig, ServerConfig, StoreConfig
from ..contracts.interfaces import IConfigUtility


class _Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    chroma_persist_dir: str = "./data/chroma"
    playwright_channel: str = ""
    playwright_state_path: str = "./data/jstor_auth_state.json"
    playwright_user_data_dir: str = "./data/playwright_user"
    login_email: str = Field(
        default="",
        validation_alias=AliasChoices("JSTOR_LOGIN_EMAIL", "JSTOR_RAG_LOGIN_EMAIL"),
    )
    login_password: str = Field(
        default="",
        validation_alias=AliasChoices("JSTOR_LOGIN_PASSWORD", "JSTOR_RAG_LOGIN_PASSWORD"),
    )
    embedding_model: str = "models/gemini-embedding-001"
    generation_model: str = "llama-3.1-8b-instant"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_prefix": "JSTOR_RAG_",
        "extra": "ignore",
    }


class ConfigUtility(IConfigUtility):
    def __init__(self) -> None:
        self._settings = _Settings()

    def read_ai_config(self) -> AIProviderConfig:
        s = self._settings
        return AIProviderConfig(
            gemini_api_key=s.gemini_api_key,
            groq_api_key=s.groq_api_key,
            embedding_model=s.embedding_model,
            generation_model=s.generation_model,
        )

    def read_store_config(self) -> StoreConfig:
        return StoreConfig(chroma_persist_dir=self._settings.chroma_persist_dir)

    def read_scraper_config(self) -> ScraperConfig:
        s = self._settings
        return ScraperConfig(
            playwright_channel=s.playwright_channel,
            playwright_state_path=s.playwright_state_path,
            playwright_user_data_dir=s.playwright_user_data_dir,
            login_email=s.login_email,
            login_password=s.login_password,
        )

    def read_server_config(self) -> ServerConfig:
        return ServerConfig(host=self._settings.host, port=self._settings.port)
