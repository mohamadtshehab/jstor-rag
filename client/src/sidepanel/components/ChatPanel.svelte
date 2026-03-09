<script lang="ts">
  import MessageBubble from "./MessageBubble.svelte";

  interface ChatMessage {
    role: "user" | "assistant";
    content: string;
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

<div class="panel">
  <!-- Message list -->
  <div bind:this={chatContainer} class="messages">
    {#if messages.length === 0}
      <div class="empty">
        <p class="empty-primary">Ask a question about the article.</p>
        <p class="empty-secondary">Your conversation is private to this session.</p>
      </div>
    {:else}
      {#each messages as msg}
        <MessageBubble role={msg.role} content={msg.content} />
      {/each}
    {/if}
  </div>

  <!-- Input bar -->
  <form onsubmit={handleSubmit} class="input-bar">
    <div class="input-row">
      <input
        bind:value={input}
        placeholder="Ask about the article…"
        disabled={sending}
        class="input"
        class:input--disabled={sending}
      />
      <button
        type="submit"
        disabled={!input.trim() || sending}
        aria-label="Send message"
        class="send-btn"
        class:send-btn--active={input.trim() && !sending}
      >
        <svg class="send-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
        </svg>
      </button>
    </div>
  </form>
</div>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
  }

  .empty-primary {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .empty-secondary {
    margin: 0.25rem 0 0;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .input-bar {
    padding: 0.75rem;
    border-top: 1px solid var(--border);
  }

  .input-row {
    display: flex;
    gap: 0.5rem;
  }

  .input {
    flex: 1;
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-size: 0.875rem;
    padding: 0.625rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
  }

  .input::placeholder {
    color: var(--text-muted);
  }

  .input:focus {
    border-color: var(--accent);
  }

  .input--disabled {
    opacity: 0.5;
  }

  .send-btn {
    padding: 0.625rem;
    background: var(--bg-tertiary);
    border: none;
    border-radius: var(--radius);
    cursor: not-allowed;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: background 0.15s;
  }

  .send-btn--active {
    background: var(--accent);
    cursor: pointer;
  }

  .send-btn--active:hover {
    background: var(--accent-hover);
  }

  .send-icon {
    width: 1rem;
    height: 1rem;
    color: #fff;
  }
</style>
