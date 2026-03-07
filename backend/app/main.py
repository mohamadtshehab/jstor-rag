from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

from fastapi import FastAPI

from .gateway import ingestion_routes, query_routes, websocket_routes


ALLOWED_ORIGINS = frozenset({
    "http://localhost:5173",
    "chrome-extension://dliiomihkadghmabmkjphcmllkjifigc",
})


class ExtensionCORSMiddleware(BaseHTTPMiddleware):
    """Adds CORS headers for Chrome extension and localhost origins."""

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        if origin not in ALLOWED_ORIGINS:
            return await call_next(request)

        if request.method == "OPTIONS":
            return PlainTextResponse(
                "OK",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                },
            )

        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = origin
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title="JSTOR RAG API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(ExtensionCORSMiddleware)

app.include_router(ingestion_routes.router)
app.include_router(query_routes.router)
app.include_router(websocket_routes.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
