<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useOperationStore } from '../../stores/operation'
import { listOperations } from '../../api/operation'
import { useRoute } from 'vue-router'
import ActivityFeed from '../../components/operation/ActivityFeed.vue'
import DecisionCard from '../../components/operation/DecisionCard.vue'
import OperationInspector from '../../components/operation/OperationInspector.vue'
import type { OperationStage, OperationType } from '../../schemas/operation'

const store = useOperationStore()
const route = useRoute()

const stageFilter = ref<OperationStage | ''>('')
const typeFilter = ref<OperationType | ''>('')

const stageLabel: Record<string, string> = {
  pending: 'Pending',
  running: 'Running',
  'waiting-decision': 'Waiting for decision',
  blocked: 'Blocked',
  completed: 'Completed',
  cancelled: 'Cancelled',
  failed: 'Failed',
}

const stageIcon: Record<string, string> = {
  pending: '○',
  running: '◑',
  'waiting-decision': '◈',
  blocked: '⊗',
  completed: '●',
  cancelled: '⊘',
  failed: '✕',
}

const allStages: OperationStage[] = ['pending','running','waiting-decision','blocked','completed','cancelled','failed']
const allTypes: OperationType[] = ['upload/import','agent-patch/report','memory-ingestion','terminal-command','browser-capture/download','repo-import/index']

const filteredOps = ref(store.operations)

async function reload() {
  const resp = await listOperations({
    stage: stageFilter.value || undefined,
    type: typeFilter.value || undefined,
  })
  store.load(resp.operations)
  filteredOps.value = resp.operations
}

watch([stageFilter, typeFilter], () => reload())

onMounted(async () => {
  // Pre-select from query param if present
  const preselect = route.query.id ? String(route.query.id) : null
  await reload()
  if (preselect) store.select(preselect)
})

function openInspector(id: string) {
  store.select(id)
}

function handleDecision(opId: string, decisionId: string, optionId: string) {
  store.resolveDecision(opId, decisionId, optionId)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">Operation Plane</h2>
      <p class="page-desc">Workspace composition layer — active mutations, decisions, artifacts, and governance.</p>
    </div>

    <!-- Filters -->
    <div class="filters" role="search" aria-label="Filter operations">
      <label class="filter-group">
        <span class="filter-label">Stage</span>
        <select v-model="stageFilter" class="filter-select" aria-label="Filter by stage">
          <option value="">All stages</option>
          <option v-for="s in allStages" :key="s" :value="s">{{ stageLabel[s] ?? s }}</option>
        </select>
      </label>
      <label class="filter-group">
        <span class="filter-label">Type</span>
        <select v-model="typeFilter" class="filter-select" aria-label="Filter by operation type">
          <option value="">All types</option>
          <option v-for="t in allTypes" :key="t" :value="t">{{ t }}</option>
        </select>
      </label>
    </div>

    <!-- Operation list -->
    <ul class="op-list" role="list" aria-label="Operations">
      <li v-if="!filteredOps.length" class="empty">No operations match the current filters.</li>
      <li
        v-for="op in filteredOps"
        :key="op.id"
        class="op-card"
        :data-stage="op.stage"
      >
        <button class="op-card-inner" @click="openInspector(op.id)" :aria-label="`Open inspector for: ${op.title}`">
          <div class="op-card-top">
            <span class="op-icon" aria-hidden="true">{{ stageIcon[op.stage] ?? '·' }}</span>
            <span class="op-title">{{ op.title }}</span>
            <span class="op-stage-badge" :data-stage="op.stage" :aria-label="`Stage: ${stageLabel[op.stage]}`">
              {{ stageLabel[op.stage] ?? op.stage }}
            </span>
          </div>
          <div class="op-meta">
            <span class="meta-pill">{{ op.type }}</span>
            <span class="meta-pill actor">{{ op.actor }}</span>
            <time class="meta-ts">{{ new Date(op.updatedAt).toLocaleString() }}</time>
          </div>
          <p v-if="op.detail" class="op-detail">{{ op.detail }}</p>
        </button>

        <!-- Inline decisions for waiting-decision ops -->
        <div v-if="op.stage === 'waiting-decision' && op.decisions.length" class="inline-decisions">
          <DecisionCard
            v-for="dec in op.decisions"
            :key="dec.id"
            :decision="dec"
            @choose="optId => handleDecision(op.id, dec.id, optId)"
          />
        </div>

        <!-- Inline activity feed (collapsed) -->
        <details class="op-events" v-if="op.events.length">
          <summary class="events-summary">Activity ({{ op.events.length }})</summary>
          <ActivityFeed :events="op.events" />
        </details>
      </li>
    </ul>

    <!-- Inspector overlay -->
    <OperationInspector />
  </div>
</template>

<style scoped>
.page{display:grid;gap:18px;padding:18px;padding-bottom:80px}
.page-header{display:grid;gap:4px}
.page-title{margin:0;font-size:22px;font-weight:700}
.page-desc{margin:0;opacity:.7;font-size:13px}

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

.op-list{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.empty{font-size:13px;opacity:.6;padding:16px 0}

.op-card{
  border:1px solid rgba(0,0,0,.12);
  border-radius:14px;
  overflow:hidden;
  display:grid;
}
.op-card[data-stage="running"]{border-color:rgba(0,80,200,.25)}
.op-card[data-stage="waiting-decision"]{border-color:rgba(200,120,0,.3)}
.op-card[data-stage="blocked"]{border-color:rgba(200,40,0,.3)}
.op-card[data-stage="failed"]{border-color:rgba(200,0,0,.25)}
.op-card[data-stage="completed"]{border-color:rgba(0,120,0,.2);opacity:.8}

.op-card-inner{
  text-align:left;
  background:transparent;
  border:0;
  padding:14px 16px;
  cursor:pointer;
  display:grid;
  gap:6px;
}
.op-card-inner:hover{background:rgba(0,0,0,.025)}

.op-card-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.op-icon{font-size:16px;flex-shrink:0;font-variant-emoji:text}
.op-title{font-weight:650;font-size:14px;flex:1;min-width:0}
.op-stage-badge{
  font-size:11px;
  border:1px solid rgba(0,0,0,.14);
  border-radius:999px;
  padding:2px 8px;
  flex-shrink:0;
}
.op-stage-badge[data-stage="running"]{background:rgba(0,80,200,.07);border-color:rgba(0,80,200,.25)}
.op-stage-badge[data-stage="waiting-decision"]{background:rgba(200,120,0,.07);border-color:rgba(200,120,0,.25)}
.op-stage-badge[data-stage="blocked"]{background:rgba(200,40,0,.07);border-color:rgba(200,40,0,.25)}
.op-stage-badge[data-stage="completed"]{background:rgba(0,120,0,.07);border-color:rgba(0,120,0,.25)}
.op-stage-badge[data-stage="failed"]{background:rgba(200,0,0,.07);border-color:rgba(200,0,0,.25)}

.op-meta{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.meta-pill{
  font-size:11px;
  border:1px solid rgba(0,0,0,.12);
  border-radius:999px;
  padding:2px 8px;
  background:rgba(0,0,0,.025);
}
.actor{font-weight:600}
.meta-ts{font-size:11px;opacity:.55}
.op-detail{margin:0;font-size:12px;opacity:.8;line-height:1.5}

.inline-decisions{padding:0 16px 14px;display:grid;gap:8px}
.op-events{padding:0 16px 12px}
.events-summary{
  font-size:12px;
  opacity:.65;
  cursor:pointer;
  padding:4px 0;
  list-style:none;
}
.events-summary::-webkit-details-marker{display:none}
.events-summary::before{content:'▶ ';font-size:10px}
details[open] .events-summary::before{content:'▼ '}
</style>
