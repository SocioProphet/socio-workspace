<script setup lang="ts">
import { onMounted } from 'vue'
import { useOperationStore } from '../../stores/operation'
import { listOperations } from '../../api/operation'

const store = useOperationStore()

const stageIcon: Record<string, string> = {
  pending: '○',
  running: '◑',
  'waiting-decision': '◈',
  blocked: '⊗',
  completed: '●',
  cancelled: '⊘',
  failed: '✕',
}

const stageLabel: Record<string, string> = {
  pending: 'Pending',
  running: 'Running',
  'waiting-decision': 'Waiting for decision',
  blocked: 'Blocked',
  completed: 'Completed',
  cancelled: 'Cancelled',
  failed: 'Failed',
}

onMounted(async () => {
  if (!store.operations.length) {
    const resp = await listOperations()
    store.load(resp.operations)
  }
})

function openInspector(id: string) {
  store.select(id)
}
</script>

<template>
  <div
    v-if="store.active.length"
    class="tray"
    role="region"
    aria-label="Active operations tray"
  >
    <div class="tray-label" aria-hidden="true">Operations</div>
    <ul class="tray-list" role="list">
      <li
        v-for="op in store.active"
        :key="op.id"
        class="tray-item"
        :data-stage="op.stage"
      >
        <button
          class="tray-btn"
          @click="openInspector(op.id)"
          :aria-label="`${stageLabel[op.stage] ?? op.stage}: ${op.title}. Press to open inspector.`"
        >
          <span class="tray-icon" aria-hidden="true">{{ stageIcon[op.stage] ?? '·' }}</span>
          <span class="tray-title">{{ op.title }}</span>
          <span class="tray-stage">{{ stageLabel[op.stage] ?? op.stage }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.tray{
  position:fixed;
  bottom:0;
  left:0;
  right:0;
  background:rgba(255,255,255,.97);
  border-top:1px solid rgba(0,0,0,.1);
  display:flex;
  align-items:center;
  gap:12px;
  padding:8px 18px;
  z-index:100;
  box-shadow:0 -2px 12px rgba(0,0,0,.08);
  backdrop-filter:blur(6px);
  min-height:44px;
}
.tray-label{
  font-size:11px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.08em;
  opacity:.5;
  flex-shrink:0;
}
.tray-list{
  display:flex;
  gap:6px;
  list-style:none;
  margin:0;
  padding:0;
  flex-wrap:wrap;
  overflow:hidden;
}
.tray-item{display:contents}
.tray-btn{
  display:flex;
  align-items:center;
  gap:6px;
  border:1px solid rgba(0,0,0,.14);
  border-radius:999px;
  padding:4px 12px;
  background:rgba(0,0,0,.02);
  cursor:pointer;
  font-size:12px;
  max-width:280px;
  overflow:hidden;
}
.tray-btn:hover{background:rgba(0,0,0,.06)}
.tray-item[data-stage="running"] .tray-btn{border-color:rgba(0,80,200,.35);background:rgba(0,80,200,.05)}
.tray-item[data-stage="waiting-decision"] .tray-btn{border-color:rgba(200,120,0,.35);background:rgba(200,120,0,.05)}
.tray-item[data-stage="blocked"] .tray-btn{border-color:rgba(200,40,0,.35);background:rgba(200,40,0,.05)}
.tray-icon{flex-shrink:0;font-variant-emoji:text}
.tray-title{
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
  font-weight:500;
}
.tray-stage{
  flex-shrink:0;
  opacity:.6;
  font-size:11px;
}
</style>
