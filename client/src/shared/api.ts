import type { AnswerResponse, IngestionResult } from "./types";

const BASE_URL = "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function ingestArticle(url: string): Promise<IngestionResult> {
  return post<IngestionResult>("/ingest", { url });
}

export async function queryArticle(
  documentId: string,
  question: string
): Promise<AnswerResponse> {
  return post<AnswerResponse>("/query", {
    document_id: documentId,
    question,
  });
}

export function createWebSocket(
  onMessage: (event: string, data: Record<string, unknown>) => void
): WebSocket {
  const ws = new WebSocket(`ws://localhost:8000/ws`);
  ws.addEventListener("message", (e) => {
    const parsed = JSON.parse(e.data);
    onMessage(parsed.event, parsed.data);
  });
  return ws;
}
