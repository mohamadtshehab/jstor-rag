import type {
  AnswerResponse,
  ExtensionMessage,
  IngestionResult,
} from "../shared/types";
import { ingestArticle, queryArticle, streamQuery } from "../shared/api";

let currentDocumentId: string | null = null;

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(console.error);

chrome.runtime.onMessage.addListener(
  (
    msg: ExtensionMessage,
    _sender: chrome.runtime.MessageSender,
    sendResponse: (response: unknown) => void
  ) => {
    handleMessage(msg)
      .then(sendResponse)
      .catch((err) =>
        sendResponse({ type: "ERROR", payload: (err as Error).message })
      );
    return true;
  }
);

async function handleMessage(
  msg: ExtensionMessage
): Promise<ExtensionMessage> {
  switch (msg.type) {
    case "INGEST_ARTICLE": {
      const { url } = msg.payload as { url: string };
      const result: IngestionResult = await ingestArticle(url);
      currentDocumentId = result.document_id;
      await chrome.storage.session.set({
        documentId: result.document_id,
        articleTitle: result.article_title,
      });
      return { type: "INGESTION_COMPLETE", payload: result };
    }

    case "QUERY_ARTICLE": {
      const { question } = msg.payload as { question: string };
      const stored = await chrome.storage.session.get("documentId");
      const docId: string | undefined =
        currentDocumentId || (stored.documentId as string | undefined);

      if (!docId) {
        return {
          type: "ERROR",
          payload: "No article ingested. Open an article on JSTOR first.",
        };
      }

      const answer: AnswerResponse = await queryArticle(docId, question);
      return { type: "QUERY_RESULT", payload: answer };
    }

    case "STREAM_QUERY": {
      const { question } = msg.payload as { question: string };
      const stored = await chrome.storage.session.get("documentId");
      const docId: string | undefined =
        currentDocumentId || (stored.documentId as string | undefined);

      if (!docId) {
        return {
          type: "ERROR",
          payload: "No article ingested. Open an article on JSTOR first.",
        };
      }

      // Fire-and-forget; server will publish deltas over websocket
      streamQuery(docId, question).catch(console.error);
      return { type: "STREAM_STARTED" };
    }

    default:
      return { type: "ERROR", payload: `Unknown message type: ${msg.type}` };
  }
}
