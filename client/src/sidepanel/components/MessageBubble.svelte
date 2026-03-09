<script lang="ts">
  interface Props {
    role: "user" | "assistant";
    content: string;
  }

  let { role, content }: Props = $props();
</script>

<div class="flex {role === 'user' ? 'justify-end' : 'justify-start'}">
  <div
    class="max-w-[85%] px-3.5 py-2.5 text-sm leading-relaxed"
    style="
      background: {role === 'user' ? 'var(--accent)' : 'var(--bg-tertiary)'};
      color: {role === 'user' ? '#fff' : 'var(--text-primary)'};
      border-radius: var(--radius);
      border-bottom-right-radius: {role === 'user' ? '0' : 'var(--radius)'};
      border-bottom-left-radius: {role === 'assistant' ? '0' : 'var(--radius)'};
    "
  >
    <p class="whitespace-pre-wrap">{content}</p>
  </div>
</div>
