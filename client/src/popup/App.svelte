<script lang="ts">
  let apiUrl = $state("http://localhost:8000");
  let status = $state<"checking" | "connected" | "disconnected">("checking");
  let saved = $state(false);

  async function checkConnection() {
    status = "checking";
    try {
      const res = await fetch(`${apiUrl}/health`);
      status = res.ok ? "connected" : "disconnected";
    } catch {
      status = "disconnected";
    }
  }

  function saveSettings() {
    chrome.storage.local.set({ apiUrl });
    saved = true;
    setTimeout(() => (saved = false), 2000);
    checkConnection();
  }

  $effect(() => {
    chrome.storage.local.get("apiUrl").then((data) => {
      if (data.apiUrl) apiUrl = data.apiUrl;
      checkConnection();
    });
  });
</script>

<div class="w-[320px] p-5">
  <div class="flex items-center gap-2.5 mb-5">
    <div class="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
      <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    </div>
    <div>
      <h1 class="text-sm font-semibold">JSTOR RAG</h1>
      <p class="text-xs text-slate-400">v0.1.0</p>
    </div>
  </div>

  <div class="space-y-4">
    <div>
      <label for="api-url" class="block text-xs font-medium text-slate-300 mb-1.5">
        Backend API URL
      </label>
      <input
        id="api-url"
        bind:value={apiUrl}
        class="w-full bg-slate-800 text-sm text-slate-100 rounded-lg px-3 py-2
               border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
    </div>

    <div class="flex items-center gap-2">
      <div
        class="w-2 h-2 rounded-full"
        class:bg-green-500={status === "connected"}
        class:bg-red-500={status === "disconnected"}
        class:bg-yellow-500={status === "checking"}
      ></div>
      <span class="text-xs text-slate-400">
        {status === "connected" ? "Connected" : status === "checking" ? "Checking…" : "Disconnected"}
      </span>
    </div>

    <div class="flex gap-2">
      <button
        onclick={saveSettings}
        class="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs
               font-medium transition-colors"
      >
        {saved ? "Saved!" : "Save"}
      </button>
      <button
        onclick={checkConnection}
        class="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-xs
               font-medium transition-colors"
      >
        Test
      </button>
    </div>
  </div>
</div>
