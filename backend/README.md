# JSTOR RAG — Backend

FastAPI backend for the JSTOR RAG Chrome Extension.

## Setup

```bash
cp .env.example .env
# Fill in your GEMINI_API_KEY
uv sync
uv run uvicorn app.main:app --reload
```
