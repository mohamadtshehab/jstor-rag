<script lang="ts">
  import type { Citation } from "../../shared/types";

  interface Props {
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
  }

  let { role, content, citations = [] }: Props = $props();

  function handleCitationClick(chunkId: string) {
    chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, {
          type: "HIGHLIGHT_CITATIONS",
          payload: citations?.map((c) => c.locator) || [],
        });
      }
    });
  }
</script>

<div class="flex {role === 'user' ? 'justify-end' : 'justify-start'}">
  <div
    class="max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed
           {role === 'user'
             ? 'bg-blue-600 text-white rounded-br-md'
             : 'bg-slate-700/60 text-slate-100 rounded-bl-md'}"
  >
    <p class="whitespace-pre-wrap">{content}</p>

    {#if citations && citations.length > 0}
      <div class="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/10">
        {#each citations as citation}
          <button
            onclick={() => handleCitationClick(citation.locator.chunkId)}
            class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300
                   hover:bg-blue-500/30 transition-colors cursor-pointer"
            title="{citation.locator.logicalSection}"
          >
            {citation.marker}
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>
