<script setup>
defineProps({ sources: { type: Array, default: () => [] } })
</script>

<template>
  <details v-if="sources.length" class="source-list">
    <summary>本轮查阅的记录 · {{ sources.length }} 项</summary>
    <p class="muted small">保留生成时的文字快照，方便核对。用户陈述与材料记录均未经独立核验。</p>
    <details v-for="source in sources" :key="source.ref" class="source-record">
      <summary><span>{{ source.label }}</span><span class="badge">{{ source.status }}</span><code>{{ source.ref }}</code></summary>
      <p class="preserve">{{ source.text }}</p>
    </details>
  </details>
</template>
