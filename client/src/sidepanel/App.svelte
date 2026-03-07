<script lang="ts">
  import ChatPanel from "./components/ChatPanel.svelte";
  import IngestionStatus from "./components/IngestionStatus.svelte";
  import type { AnswerResponse } from "../shared/types";

  let articleTitle = $state("");
  let documentId = $state<string | null>(null);
  let ingesting = $state(false);
  let error = $state("");
  let messages = $state<Array<{ role: "user" | "assistant"; content: string; citations?: AnswerResponse["citations"] }>>([]);

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

      documentId = ingestResponse.payload.document_id;
      articleTitle = ingestResponse.payload.article_title || "Untitled Article";
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
      messages = [
        ...messages,
        { role: "assistant", content: answer.answer_text, citations: answer.citations },
      ];
    } catch (e) {
      messages = [...messages, { role: "assistant", content: `Error: ${(e as Error).message}` }];
    }
  }

  $effect(() => {
    chrome.storage.session.get(["documentId", "articleTitle"]).then((data) => {
      if (data.documentId) documentId = data.documentId;
      if (data.articleTitle) articleTitle = data.articleTitle;
    });
  });
</script>

<div class="flex flex-col h-screen">
  <header class="flex items-center gap-2 px-4 py-3 border-b border-slate-700 bg-slate-900/80">
    <div class="w-2 h-2 rounded-full" class:bg-green-500={!!documentId} class:bg-slate-500={!documentId}></div>
    <h1 class="text-sm font-semibold tracking-tight truncate">
      {articleTitle || "JSTOR RAG"}
    </h1>
  </header>

  <main class="flex-1 overflow-hidden">
    {#if !documentId}
      <IngestionStatus {ingesting} {error} onIngest={handleIngest} />
    {:else}
      <ChatPanel {messages} onSend={handleQuery} />
    {/if}
  </main>
</div>
