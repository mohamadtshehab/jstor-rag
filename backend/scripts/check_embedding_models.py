#!/usr/bin/env -S uv run python
"""List Google embedding models. Loads API key from .env (JSTOR_RAG_GEMINI_API_KEY)."""
import os
import sys
from pathlib import Path

# Load .env from backend root
backend_root = Path(__file__).resolve().parent.parent
env_file = backend_root / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from google import genai


def check_models():
    api_key = os.environ.get("JSTOR_RAG_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Set JSTOR_RAG_GEMINI_API_KEY or GEMINI_API_KEY in .env", file=sys.stderr)
        sys.exit(1)
    client = genai.Client(api_key=api_key)
    for model in client.models.list():
        methods = getattr(model, "supported_methods", None) or getattr(
            model, "supported_actions", []
        )
        if "embedContent" in methods:
            print(f"Supported: {model.name}")


if __name__ == "__main__":
    check_models()
