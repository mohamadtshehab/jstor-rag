<script lang="ts">
  import ChatPanel from "./components/ChatPanel.svelte";
  import IngestionStatus from "./components/IngestionStatus.svelte";
  import type { AnswerResponse } from "../shared/types";

  let articleTitle = $state("");
  let documentId = $state<string | null>(null);
  let ingesting = $state(false);
  let error = $state("");
  let messages = $state<Array<{ role: "user" | "assistant"; content: string }>>([]);

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
    messages = [...messages, { role: "user", content: question }];

    try {
      const response = await chrome.runtime.sendMessage({
        type: "QUERY_ARTICLE",
        payload: { question },
      });

      if (response.type === "ERROR") {
        messages = [...messages, { role: "assistant", content: response.payload as string }];
        return;
      }

      const answer = response.payload as AnswerResponse;
      messages = [...messages, { role: "assistant", content: answer.answer_text }];
    } catch (e) {
      messages = [...messages, { role: "assistant", content: `Error: ${(e as Error).message}` }];
    }
  }

  $effect(() => {
    chrome.storage.session.get(["documentId", "articleTitle"]).then((data) => {
      documentId = (data.documentId as string | undefined) ?? null;
      articleTitle = (data.articleTitle as string | undefined) ?? "";
    });
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
