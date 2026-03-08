<script lang="ts">
  interface Props {
    role: "user" | "assistant";
    content: string;
  }

  let { role, content }: Props = $props();
</script>

<div class="flex {role === 'user' ? 'justify-end' : 'justify-start'}">
  <div
    class="max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed
           {role === 'user'
             ? 'bg-blue-600 text-white rounded-br-md'
             : 'bg-slate-700/60 text-slate-100 rounded-bl-md'}"
  >
    <p class="whitespace-pre-wrap">{content}</p>
  </div>
</div>
