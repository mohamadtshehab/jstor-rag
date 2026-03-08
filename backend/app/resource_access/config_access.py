from __future__ import annotations

from pydantic_settings import BaseSettings

from ..contracts.interfaces import IConfigAccess


class _Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    chroma_persist_dir: str = "./data/chroma"
    playwright_channel: str = ""  # "chrome" to use system Chrome (better for bot evasion)
    playwright_state_path: str = "./data/jstor_auth_state.json"  # cached login cookies
    playwright_user_data_dir: str = "./data/playwright_user"  # persistent profile for bot evasion
    login_email: str = ""
    login_password: str = ""
    embedding_model: str = "models/gemini-embedding-001"
    generation_model: str = "llama-3.1-8b-instant"  # Groq model
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_prefix": "JSTOR_RAG_",
        "extra": "ignore",
    }


class ConfigAccess(IConfigAccess):
    def __init__(self) -> None:
        self._settings = _Settings()

    def get(self, key: str, default: str = "") -> str:
        return str(getattr(self._settings, key, default))

    @property
    def settings(self) -> _Settings:
        return self._settings
