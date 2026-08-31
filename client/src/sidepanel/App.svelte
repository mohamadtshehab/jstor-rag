<script lang="ts">
  import ChatPanel from "./components/ChatPanel.svelte";
  import IngestionStatus from "./components/IngestionStatus.svelte";
  import type { AnswerResponse } from "../shared/types";

  let articleTitle = $state("");
  let documentId = $state<string | null>(null);
  let ingesting = $state(false);
  let error = $state("");
  let messages = $state<Array<{ role: "user" | "assistant"; content: string }>>([]);
  let ws: WebSocket | null = $state(null);

  async function handleIngest() {
    ingesting = true;
    error = "";

    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });

      if (!tab?.url) {
        error = "No active tab. Open a JSTOR article page.";
        return;
      }

      const ingestResponse = await chrome.runtime.sendMessage({
        type: "INGEST_ARTICLE",
        payload: { url: tab.url },
      });

      if (ingestResponse.type === "ERROR") {
        error = ingestResponse.payload as string;
        return;
      }

      const payload = ingestResponse.payload as { document_id: string; article_title?: string };
      documentId = payload.document_id;
      articleTitle = payload.article_title ?? "Untitled Article";
    } catch (e) {
      error = (e as Error).message;
    } finally {
      ingesting = false;
    }
  }

  async function handleQuery(question: string) {
    // Add user message and a placeholder assistant message for streaming deltas
    messages = [...messages, { role: "user", content: question }];
    messages = [...messages, { role: "assistant", content: "" }];

    try {
      const response = await chrome.runtime.sendMessage({
        type: "STREAM_QUERY",
        payload: { question },
      });

      if (response.type === "ERROR") {
        messages = [...messages, { role: "assistant", content: response.payload as string }];
        return;
      }

      // STREAM_STARTED returned; actual content arrives via websocket events
      return;
    } catch (e) {
      messages = [...messages, { role: "assistant", content: `Error: ${(e as Error).message}` }];
    }
  }

  $effect(() => {
    chrome.storage.session.get(["documentId", "articleTitle"]).then((data) => {
      documentId = (data.documentId as string | undefined) ?? null;
      articleTitle = (data.articleTitle as string | undefined) ?? "";
    });

    // create websocket connection to receive streaming deltas
    if (!ws) {
      // Dynamic import to use the shared helper
      import("../shared/api").then(({ createWebSocket }) => {
        ws = createWebSocket((event, data) => {
          if (event !== "StreamingResponse") return;
          const docId = (data.document_id as string) || null;
          const delta = (data.delta as string) || "";
          const done = Boolean(data.done);

          // Append delta to last assistant message
          const lastIdx = messages.length - 1;
          if (lastIdx >= 0 && messages[lastIdx].role === "assistant") {
            messages[lastIdx] = { ...messages[lastIdx], content: messages[lastIdx].content + delta };
          } else {
            messages = [...messages, { role: "assistant", content: delta }];
          }

          if (done) {
            // Optionally mark completion; no-op for now
          }
        });
      });
    }
  });
</script>

<div class="flex flex-col h-screen" style="background: var(--bg-primary); color: var(--text-primary);">
  <!-- Header -->
  <header
    class="flex items-center gap-2.5 px-4 py-3"
    style="
      border-bottom: 1px solid var(--border);
      background: var(--bg-secondary);
    "
  >
    <!-- Status dot -->
    <div
      class="w-2 h-2 rounded-full flex-shrink-0"
      style={documentId ? "background: var(--success);" : "background: var(--bg-tertiary);"}
    ></div>

    <!-- Title / wordmark -->
    <div class="flex items-center gap-2 min-w-0 flex-1">
      {#if articleTitle}
        <span class="text-xs font-medium truncate" style="color: var(--text-secondary);">{articleTitle}</span>
      {:else}
        <span class="text-sm font-semibold tracking-tight" style="color: var(--accent);">JSTOR</span>
        <span class="text-sm font-semibold tracking-tight">RAG</span>
      {/if}
    </div>
  </header>

  <main class="flex-1 overflow-hidden">
    {#if !documentId}
      <IngestionStatus {ingesting} {error} onIngest={handleIngest} />
    {:else}
      <ChatPanel {messages} onSend={handleQuery} />
    {/if}
  </main>
</div>
