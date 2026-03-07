<script lang="ts">
  import type { AnswerResponse } from "../../shared/types";
  import MessageBubble from "./MessageBubble.svelte";

  interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    citations?: AnswerResponse["citations"];
  }

  interface Props {
    messages: ChatMessage[];
    onSend: (question: string) => void;
  }

  let { messages, onSend }: Props = $props();

  let input = $state("");
  let chatContainer: HTMLDivElement | undefined = $state();
  let sending = $state(false);

  $effect(() => {
    if (messages.length && chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  });

  async function handleSubmit(e: Event) {
    e.preventDefault();
    const q = input.trim();
    if (!q || sending) return;
    input = "";
    sending = true;
    await onSend(q);
    sending = false;
  }
</script>

<div class="flex flex-col h-full">
  <div bind:this={chatContainer} class="flex-1 overflow-y-auto p-4 space-y-3">
    {#if messages.length === 0}
      <div class="flex flex-col items-center justify-center h-full text-center text-slate-400">
        <p class="text-sm">Ask a question about the article.</p>
        <p class="text-xs mt-1">Citations will highlight the source text on the page.</p>
      </div>
    {:else}
      {#each messages as msg}
        <MessageBubble role={msg.role} content={msg.content} citations={msg.citations} />
      {/each}
    {/if}
  </div>

  <form onsubmit={handleSubmit} class="p-3 border-t border-slate-700">
    <div class="flex gap-2">
      <input
        bind:value={input}
        placeholder="Ask about the article…"
        disabled={sending}
        class="flex-1 bg-slate-800 text-sm text-slate-100 placeholder:text-slate-500
               rounded-xl px-4 py-2.5 border border-slate-600 focus:border-blue-500
               focus:outline-none transition-colors disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={!input.trim() || sending}
        aria-label="Send message"
        class="p-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600
               disabled:cursor-not-allowed rounded-xl transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
        </svg>
      </button>
    </div>
  </form>
</div>
