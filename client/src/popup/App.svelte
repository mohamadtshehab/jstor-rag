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

<div class="root">
  <!-- Header -->
  <div class="header">
    <div class="icon-box">
      <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    </div>
    <div>
      <h1 class="title">JSTOR RAG</h1>
      <p class="subtitle">v0.1.0</p>
    </div>
  </div>

  <div class="fields">
    <!-- API URL -->
    <div>
      <label for="api-url" class="label">Backend API URL</label>
      <input id="api-url" class="input" bind:value={apiUrl} />
    </div>

    <!-- Status -->
    <div class="status-row">
      <div
        class="dot"
        class:dot--connected={status === "connected"}
        class:dot--checking={status === "checking"}
        class:dot--disconnected={status === "disconnected"}
      ></div>
      <span class="status-text">
        {status === "connected" ? "Connected" : status === "checking" ? "Checking…" : "Disconnected"}
      </span>
    </div>

    <!-- Actions -->
    <div class="actions">
      <button class="btn btn--primary" onclick={saveSettings}>
        {saved ? "Saved!" : "Save"}
      </button>
      <button class="btn btn--secondary" onclick={checkConnection}>Test</button>
    </div>
  </div>
</div>

<style>
  .root {
    width: 320px;
    padding: 1.25rem;
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  .header {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    margin-bottom: 1.25rem;
  }

  .icon-box {
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent-subtle);
    border-radius: var(--radius);
    flex-shrink: 0;
  }

  .icon {
    width: 1rem;
    height: 1rem;
    color: var(--accent);
  }

  .title {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .subtitle {
    margin: 0;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .label {
    display: block;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 0.375rem;
  }

  .input {
    width: 100%;
    box-sizing: border-box;
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-size: 0.875rem;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
  }

  .input:focus {
    border-color: var(--accent);
  }

  .status-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .dot--connected  { background: var(--success); }
  .dot--checking   { background: var(--warning); }
  .dot--disconnected { background: var(--accent); }

  .status-text {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .actions {
    display: flex;
    gap: 0.5rem;
  }

  .btn {
    padding: 0.5rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 500;
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    transition: background 0.15s;
    font-family: inherit;
  }

  .btn--primary {
    flex: 1;
    background: var(--accent);
    color: #fff;
  }

  .btn--primary:hover {
    background: var(--accent-hover);
  }

  .btn--secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .btn--secondary:hover {
    background: var(--border);
  }
</style>
