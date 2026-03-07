export interface SourceLocator {
  chunkId: string;
  logicalSection: string;
  startOffset: number;
  endOffset: number;
  contextSnippet: string;
}

export interface Citation {
  marker: string;
  locator: SourceLocator;
}

export interface AnswerResponse {
  document_id: string;
  answer_text: string;
  citations: Citation[];
}

export interface IngestionResult {
  document_id: string;
  total_chunks: number;
  status: string;
  article_title: string;
}

export type MessageType =
  | "HIGHLIGHT_CITATIONS"
  | "CLEAR_HIGHLIGHTS"
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
