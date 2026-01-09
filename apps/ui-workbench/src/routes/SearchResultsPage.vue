<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ResultCard from '../components/search/ResultCard.vue'
import { useSearchStore } from '../stores/search'
import { search } from '../api/search'
import type { SearchResult } from '../schemas/search'

const route = useRoute()
const router = useRouter()
const store = useSearchStore()

const q = computed(() => String(route.query.q ?? '').trim())
const mode = computed(() => store.mode)

const loading = ref(false)
const results = ref<SearchResult[]>([])

async function runSearch() {
  if (!q.value) { results.value = []; return }
  loading.value = true
  try {
    store.pushRecent(q.value)
    const resp = await search({ q: q.value, mode: mode.value, page: 1 })
    results.value = resp.results
  } finally {
    loading.value = false
  }
}

function setMode(m: 'blended'|'local'|'global') { store.setMode(m) }

function openEntity(r: SearchResult) {
  if (r.kind === 'entity') router.push({ path: `/entity/company/${encodeURIComponent(r.id)}` })
  else if (r.kind === 'local_file') router.push({ path: `/entity/file/${encodeURIComponent(r.id)}` })
  else router.push({ path: `/entity/doc/${encodeURIComponent(r.id)}` })
}

watch([q, mode], () => { runSearch() }, { immediate: true })
</script>

<template>
  <div class="page">
    <div class="top">
      <div class="qline">
        <div class="label">query</div>
        <div class="q">{{ q || '(empty)' }}</div>
      </div>

      <div class="modes">
        <button class="chip" :class="{ on: mode==='blended' }" @click="setMode('blended')">blended</button>
        <button class="chip" :class="{ on: mode==='local' }" @click="setMode('local')">local</button>
        <button class="chip" :class="{ on: mode==='global' }" @click="setMode('global')">global</button>
      </div>
    </div>

    <div v-if="loading" class="hint">searching…</div>
    <div v-else class="grid">
      <button v-for="r in results" :key="r.id" class="hit" @click="openEntity(r)">
        <ResultCard :r="r" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.page{display:grid;gap:12px;padding:18px}
.top{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:baseline}
.qline{display:grid;gap:4px}
.label{font-size:12px;opacity:.7;text-transform:uppercase;letter-spacing:.08em}
.q{font-weight:650}
.modes{display:flex;gap:8px}
.chip{border:1px solid rgba(0,0,0,.15);background:rgba(0,0,0,.02);border-radius:999px;padding:6px 10px;cursor:pointer}
.chip.on{background:rgba(0,0,0,.08)}
.grid{display:grid;gap:10px}
.hit{text-align:left;background:transparent;border:0;padding:0;cursor:pointer}
.hint{opacity:.75}
</style>
