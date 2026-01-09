<script setup lang="ts">
export type TrustLevel = 'trusted' | 'mixed' | 'untrusted'

const props = defineProps<{
  trust: TrustLevel
  title?: string
}>()

const label = props.trust
</script>

<template>
  <span class="badge" :data-trust="trust" :title="title ?? `trust: ${label}`">
    {{ label }}
  </span>
</template>

<style scoped>
.badge{
  font-size:12px;
  border:1px solid rgba(0,0,0,.12);
  border-radius:999px;
  padding:2px 8px;
  opacity:.9;
}
.badge[data-trust="trusted"]{ background: rgba(0,0,0,.04); }
.badge[data-trust="mixed"]{ background: rgba(0,0,0,.02); }
.badge[data-trust="untrusted"]{ background: rgba(0,0,0,.00); text-decoration: line-through; opacity:.7; }
</style>
