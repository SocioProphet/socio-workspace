<script setup lang="ts">
import type { SearchResult } from '../../schemas/search'
import { TrustBadge } from '@ui-kit/index'

defineProps<{ r: SearchResult }>()
</script>

<template>
  <div class="card">
    <div class="top">
      <div class="t">{{ r.title }}</div>
      <div class="m">
        <span class="p">{{ r.kind }}</span>
        <TrustBadge :trust="r.trust" />
        <span v-if="typeof r.score==='number'" class="p">score {{ r.score.toFixed(2) }}</span>
      </div>
    </div>
    <div v-if="r.snippet" class="s">{{ r.snippet }}</div>
    <div v-if="r.source" class="src">source: {{ r.source }}</div>
  </div>
</template>

<style scoped>
.card{border:1px solid rgba(0,0,0,.12);border-radius:14px;padding:12px 14px;display:grid;gap:8px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap}
.t{font-weight:650}
.m{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.p{font-size:12px;opacity:.8;border:1px solid rgba(0,0,0,.12);border-radius:999px;padding:2px 8px}
.s{opacity:.9}
.src{font-size:12px;opacity:.7}
</style>
