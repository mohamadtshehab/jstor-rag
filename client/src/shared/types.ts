export interface AnswerResponse {
  document_id: string;
  answer_text: string;
}

export interface IngestionResult {
  document_id: string;
  total_chunks: number;
  status: string;
  article_title: string;
}

export type MessageType =
  | "INGEST_ARTICLE"
  | "QUERY_ARTICLE"
  | "INGESTION_COMPLETE"
  | "QUERY_RESULT"
  | "ERROR"
  | "OPEN_SIDEPANEL";

export interface ExtensionMessage {
  type: MessageType;
  payload?: unknown;
}
