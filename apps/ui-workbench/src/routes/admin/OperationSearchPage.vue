<script setup lang="ts">
import { ref, watch } from 'vue'
import { listOperations } from '../../api/operation'
import type { Operation, OperationStage, OperationType } from '../../schemas/operation'
import { useOperationStore } from '../../stores/operation'
import OperationInspector from '../../components/operation/OperationInspector.vue'

const store = useOperationStore()

const q = ref('')
const stageFilter = ref<OperationStage | ''>('')
const typeFilter = ref<OperationType | ''>('')
const results = ref<Operation[]>([])
const loading = ref(false)

const stageLabel: Record<string, string> = {
  pending: 'Pending',
  running: 'Running',
  'waiting-decision': 'Waiting for decision',
  blocked: 'Blocked',
  completed: 'Completed',
  cancelled: 'Cancelled',
  failed: 'Failed',
}

const allStages: OperationStage[] = ['pending','running','waiting-decision','blocked','completed','cancelled','failed']
const allTypes: OperationType[] = ['upload/import','agent-patch/report','memory-ingestion','terminal-command','browser-capture/download','repo-import/index']

async function runSearch() {
  loading.value = true
  try {
    const resp = await listOperations({
      q: q.value,
      stage: stageFilter.value || undefined,
      type: typeFilter.value || undefined,
    })
    results.value = resp.operations
    store.load(resp.operations)
  } finally {
    loading.value = false
  }
}

watch([q, stageFilter, typeFilter], () => runSearch(), { immediate: true })

function openInspector(id: string) { store.select(id) }
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">Operation Search</h2>
      <p class="page-desc">Operator/admin projection — search all workspace operations.</p>
    </div>

    <!-- Search controls -->
    <div class="controls" role="search" aria-label="Operation search">
      <input
        v-model="q"
        class="search-input"
        type="search"
        placeholder="Search by title, actor, or detail…"
        aria-label="Search operations"
      />
      <div class="filters">
        <label class="filter-group">
          <span class="filter-label">Stage</span>
          <select v-model="stageFilter" class="filter-select" aria-label="Filter by stage">
            <option value="">All</option>
            <option v-for="s in allStages" :key="s" :value="s">{{ stageLabel[s] ?? s }}</option>
          </select>
        </label>
        <label class="filter-group">
          <span class="filter-label">Type</span>
          <select v-model="typeFilter" class="filter-select" aria-label="Filter by type">
            <option value="">All</option>
            <option v-for="t in allTypes" :key="t" :value="t">{{ t }}</option>
          </select>
        </label>
      </div>
    </div>

    <div v-if="loading" class="hint" role="status" aria-live="polite">Searching…</div>

    <table v-else class="results-table" aria-label="Operation search results">
      <thead>
        <tr>
          <th scope="col">Stage</th>
          <th scope="col">Title</th>
          <th scope="col">Type</th>
          <th scope="col">Actor</th>
          <th scope="col">Updated</th>
          <th scope="col"><span class="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!results.length">
          <td colspan="6" class="empty">No operations match.</td>
        </tr>
        <tr
          v-for="op in results"
          :key="op.id"
          :data-stage="op.stage"
          class="result-row"
        >
          <td>
            <span class="stage-badge" :data-stage="op.stage" :aria-label="`Stage: ${stageLabel[op.stage]}`">
              {{ stageLabel[op.stage] ?? op.stage }}
            </span>
          </td>
          <td class="title-cell">{{ op.title }}</td>
          <td><span class="type-pill">{{ op.type }}</span></td>
          <td class="actor-cell">{{ op.actor }}</td>
          <td class="ts-cell"><time :datetime="op.updatedAt">{{ new Date(op.updatedAt).toLocaleString() }}</time></td>
          <td>
            <button class="inspect-btn" @click="openInspector(op.id)" :aria-label="`Inspect: ${op.title}`">Inspect</button>
          </td>
        </tr>
      </tbody>
    </table>

    <OperationInspector />
  </div>
</template>

<style scoped>
.page{display:grid;gap:18px;padding:18px;padding-bottom:80px}
.page-header{display:grid;gap:4px}
.page-title{margin:0;font-size:22px;font-weight:700}
.page-desc{margin:0;opacity:.7;font-size:13px}

.controls{display:grid;gap:10px}
.search-input{
  border:1px solid rgba(0,0,0,.2);
  border-radius:10px;
  padding:9px 12px;
  font-size:14px;
  width:100%;
  max-width:520px;
}
.filters{display:flex;gap:12px;flex-wrap:wrap}
.filter-group{display:flex;align-items:center;gap:6px}
.filter-label{font-size:12px;font-weight:600;opacity:.65;text-transform:uppercase;letter-spacing:.06em}
.filter-select{
  border:1px solid rgba(0,0,0,.18);
  border-radius:8px;
  padding:5px 10px;
  font-size:12px;
  background:#fff;
  cursor:pointer;
}

.results-table{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}
.results-table th{
  text-align:left;
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.06em;
  opacity:.55;
  padding:6px 10px;
  border-bottom:2px solid rgba(0,0,0,.1);
}
.results-table td{
  padding:10px 10px;
  border-bottom:1px solid rgba(0,0,0,.06);
  vertical-align:middle;
}
.result-row:hover td{background:rgba(0,0,0,.02)}
.result-row[data-stage="waiting-decision"] td{background:rgba(200,120,0,.03)}
.result-row[data-stage="blocked"] td{background:rgba(200,40,0,.03)}
.result-row[data-stage="failed"] td{background:rgba(200,0,0,.025)}

.stage-badge{
  font-size:11px;
  border:1px solid rgba(0,0,0,.14);
  border-radius:999px;
  padding:2px 8px;
  white-space:nowrap;
}
.stage-badge[data-stage="running"]{background:rgba(0,80,200,.07);border-color:rgba(0,80,200,.25)}
.stage-badge[data-stage="waiting-decision"]{background:rgba(200,120,0,.07);border-color:rgba(200,120,0,.25)}
.stage-badge[data-stage="blocked"]{background:rgba(200,40,0,.07);border-color:rgba(200,40,0,.25)}
.stage-badge[data-stage="completed"]{background:rgba(0,120,0,.07);border-color:rgba(0,120,0,.25)}
.stage-badge[data-stage="failed"]{background:rgba(200,0,0,.07);border-color:rgba(200,0,0,.25)}

.title-cell{font-weight:500;max-width:280px}
.type-pill{
  font-size:11px;
  border:1px solid rgba(0,0,0,.12);
  border-radius:999px;
  padding:2px 8px;
  background:rgba(0,0,0,.025);
  white-space:nowrap;
}
.actor-cell{font-weight:600;font-size:12px}
.ts-cell{font-size:11px;opacity:.6;white-space:nowrap}

.inspect-btn{
  border:1px solid rgba(0,0,0,.16);
  border-radius:8px;
  padding:5px 10px;
  background:transparent;
  cursor:pointer;
  font-size:12px;
}
.inspect-btn:hover{background:rgba(0,0,0,.05)}

.hint{font-size:13px;opacity:.65}
.empty{text-align:center;opacity:.55;padding:20px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
</style>
