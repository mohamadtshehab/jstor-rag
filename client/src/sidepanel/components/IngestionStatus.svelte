<script lang="ts">
  interface Props {
    ingesting: boolean;
    error: string;
    onIngest: () => void;
  }

  let { ingesting, error, onIngest }: Props = $props();
</script>

<div class="container">
  <!-- Icon -->
  <div class="icon-box">
    <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
        d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  </div>

  <!-- Copy -->
  <div class="copy">
    <h2 class="heading">Analyze Article</h2>
    <p class="body">
      Navigate to a JSTOR article and click below to ingest it for AI-powered Q&amp;A.
    </p>
  </div>

  <!-- Error -->
  {#if error}
    <p class="error">{error}</p>
  {/if}

  <!-- CTA -->
  <button
    onclick={onIngest}
    disabled={ingesting}
    class="btn"
    class:btn--disabled={ingesting}
  >
    {#if ingesting}
      <svg class="spinner" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      Processing…
    {:else}
      Ingest Current Article
    {/if}
  </button>
</div>

<style>
  .container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 1.5rem;
    text-align: center;
    gap: 1.5rem;
  }

  .icon-box {
    width: 4rem;
    height: 4rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent-subtle);
    border-radius: var(--radius);
  }

  .icon {
    width: 2rem;
    height: 2rem;
    color: var(--accent);
  }

  .copy {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .heading {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
  }

  .body {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
    max-width: 240px;
  }

  .error {
    margin: 0;
    font-size: 0.875rem;
    color: var(--error);
    background: rgba(204, 34, 0, 0.1);
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius);
  }

  .btn {
    padding: 0.625rem 1.25rem;
    background: var(--accent);
    color: #fff;
    font-size: 0.875rem;
    font-weight: 500;
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: background 0.15s;
    font-family: inherit;
  }

  .btn:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .btn--disabled {
    background: var(--bg-tertiary);
    color: var(--text-muted);
    cursor: not-allowed;
  }

  .spinner {
    width: 1rem;
    height: 1rem;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
