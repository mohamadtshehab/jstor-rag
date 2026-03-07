<script lang="ts">
  interface Props {
    ingesting: boolean;
    error: string;
    onIngest: () => void;
  }

  let { ingesting, error, onIngest }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center h-full px-6 text-center gap-6">
  <div class="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center">
    <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
        d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  </div>

  <div>
    <h2 class="text-lg font-semibold mb-1">Analyze Article</h2>
    <p class="text-sm text-slate-400 max-w-[240px]">
      Navigate to a JSTOR article and click below to ingest it for AI-powered Q&A.
    </p>
  </div>

  {#if error}
    <p class="text-sm text-red-400 bg-red-400/10 px-3 py-2 rounded-lg">{error}</p>
  {/if}

  <button
    onclick={onIngest}
    disabled={ingesting}
    class="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600
           disabled:cursor-not-allowed rounded-lg text-sm font-medium
           transition-colors duration-150 flex items-center gap-2"
  >
    {#if ingesting}
      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      Processing…
    {:else}
      Ingest Current Article
    {/if}
  </button>
</div>
