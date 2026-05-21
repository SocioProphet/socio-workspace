<script setup lang="ts">
import { computed } from 'vue'
import { useOperationStore } from '../../stores/operation'
import DecisionCard from './DecisionCard.vue'
import ActivityFeed from './ActivityFeed.vue'

const store = useOperationStore()
const op = computed(() => store.selected)

function close() { store.closeInspector() }

const stageLabel: Record<string, string> = {
  pending: 'Pending',
  running: 'Running',
  'waiting-decision': 'Waiting for decision',
  blocked: 'Blocked by policy',
  completed: 'Completed',
  cancelled: 'Cancelled',
  failed: 'Failed',
}

function handleDecision(decisionId: string, optionId: string) {
  if (!op.value) return
  store.resolveDecision(op.value.id, decisionId, optionId)
}
</script>

<template>
  <div
    v-if="store.inspectorOpen && op"
    class="inspector-overlay"
    role="dialog"
    aria-modal="true"
    :aria-label="`Operation inspector: ${op.title}`"
    @keydown.esc="close"
    tabindex="-1"
  >
    <div class="inspector-panel">
      <!-- Header -->
      <div class="insp-header">
        <div class="insp-title-row">
          <h2 class="insp-title">{{ op.title }}</h2>
          <button class="close-btn" @click="close" aria-label="Close inspector">✕</button>
        </div>
        <div class="meta-row">
          <span class="meta-pill" :data-stage="op.stage" role="status" :aria-label="`Stage: ${stageLabel[op.stage]}`">
            {{ stageLabel[op.stage] ?? op.stage }}
          </span>
          <span class="meta-pill">{{ op.type }}</span>
          <span class="meta-pill actor">{{ op.actor }}</span>
          <time class="meta-ts">{{ new Date(op.updatedAt).toLocaleString() }}</time>
        </div>
      </div>

      <!-- Detail -->
      <div v-if="op.detail" class="section detail-section">
        <p class="detail-text">{{ op.detail }}</p>
      </div>

      <!-- Policy block -->
      <div v-if="op.policyBlock" class="section policy-block" role="alert" aria-label="Policy block">
        <div class="section-title">Policy block</div>
        <div class="policy-id">{{ op.policyBlock.policyId }}</div>
        <p class="policy-reason">{{ op.policyBlock.reason }}</p>
        <div class="actor-line">
          <span class="actor-label">Responsible actor:</span>
          <span>{{ op.policyBlock.responsibleActor }}</span>
        </div>
        <ul v-if="op.policyBlock.remediationOptions.length" class="remediation-list" aria-label="Remediation options">
          <li v-for="(rem, i) in op.policyBlock.remediationOptions" :key="i">{{ rem }}</li>
        </ul>
      </div>

      <!-- Decisions -->
      <div v-if="op.decisions.length" class="section">
        <div class="section-title">Decisions required</div>
        <DecisionCard
          v-for="dec in op.decisions"
          :key="dec.id"
          :decision="dec"
          @choose="optId => handleDecision(dec.id, optId)"
        />
      </div>

      <!-- Errors -->
      <div v-if="op.errors.length" class="section">
        <div class="section-title">Errors</div>
        <div
          v-for="(err, i) in op.errors"
          :key="i"
          class="error-card"
          role="alert"
        >
          <div class="error-code">{{ err.code }}</div>
          <p class="error-msg">{{ err.message }}</p>
          <div v-if="err.responsibleActor" class="actor-line">
            <span class="actor-label">Who can fix it:</span>
            <span>{{ err.responsibleActor }}</span>
          </div>
          <div v-if="err.safeNextAction" class="next-action">
            <span class="actor-label">Safe next action:</span> {{ err.safeNextAction }}
          </div>
          <div v-if="err.redacted" class="redacted-note">Diagnostics redacted per policy.</div>
        </div>
      </div>

      <!-- Artifacts -->
      <div v-if="op.artifacts.length" class="section">
        <div class="section-title">Artifacts</div>
        <div v-for="art in op.artifacts" :key="art.id" class="artifact-card">
          <div class="art-header">
            <span class="art-label">{{ art.label }}</span>
            <span class="meta-pill" :data-admission="art.admissionStatus">{{ art.admissionStatus }}</span>
          </div>
          <div class="art-meta">
            <span class="meta-pill">{{ art.kind }}</span>
            <span v-if="art.source" class="meta-pill">{{ art.source }}</span>
          </div>
          <!-- Artifact operation history -->
          <div v-if="art.operationHistory.length" class="art-history">
            <span class="history-label">Op history:</span>
            <span v-for="opId in art.operationHistory" :key="opId" class="history-pill">{{ opId }}</span>
          </div>
        </div>
      </div>

      <!-- Activity feed -->
      <div class="section">
        <ActivityFeed :events="op.events" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.inspector-overlay{
  position:fixed;
  inset:0;
  background:rgba(0,0,0,.35);
  z-index:200;
  display:flex;
  justify-content:flex-end;
  align-items:stretch;
}
.inspector-panel{
  width:min(560px,100vw);
  background:#fff;
  overflow-y:auto;
  display:grid;
  align-content:start;
  gap:0;
  box-shadow:-4px 0 24px rgba(0,0,0,.15);
}
.insp-header{
  padding:20px 20px 12px;
  border-bottom:1px solid rgba(0,0,0,.1);
  display:grid;
  gap:8px;
  position:sticky;
  top:0;
  background:#fff;
  z-index:1;
}
.insp-title-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.insp-title{margin:0;font-size:16px;font-weight:700;line-height:1.3}
.close-btn{
  flex-shrink:0;
  border:1px solid rgba(0,0,0,.14);
  background:transparent;
  border-radius:8px;
  padding:4px 10px;
  cursor:pointer;
  font-size:14px;
}
.meta-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.meta-pill{
  font-size:11px;
  border:1px solid rgba(0,0,0,.14);
  border-radius:999px;
  padding:2px 8px;
  background:rgba(0,0,0,.03);
}
.meta-pill[data-stage="running"]{background:rgba(0,80,200,.07);border-color:rgba(0,80,200,.25)}
.meta-pill[data-stage="waiting-decision"]{background:rgba(200,120,0,.07);border-color:rgba(200,120,0,.25)}
.meta-pill[data-stage="blocked"]{background:rgba(200,40,0,.07);border-color:rgba(200,40,0,.25)}
.meta-pill[data-stage="completed"]{background:rgba(0,120,0,.07);border-color:rgba(0,120,0,.25)}
.meta-pill[data-stage="failed"]{background:rgba(200,0,0,.07);border-color:rgba(200,0,0,.25)}
.meta-pill[data-admission="admitted"]{background:rgba(0,120,0,.07);border-color:rgba(0,120,0,.25)}
.meta-pill[data-admission="rejected"]{background:rgba(200,0,0,.07);border-color:rgba(200,0,0,.25)}
.meta-pill[data-admission="review"]{background:rgba(200,120,0,.07);border-color:rgba(200,120,0,.25)}
.meta-ts{font-size:11px;opacity:.55}
.actor{font-weight:600}

.section{padding:16px 20px;border-bottom:1px solid rgba(0,0,0,.07);display:grid;gap:10px}
.section-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;opacity:.6}
.detail-text{margin:0;line-height:1.5}

.policy-block{background:rgba(200,40,0,.03)}
.policy-id{font-size:12px;font-weight:700;font-family:monospace}
.policy-reason{margin:0;line-height:1.5}
.actor-line{display:flex;gap:6px;font-size:12px;flex-wrap:wrap}
.actor-label{font-weight:600;opacity:.75}
.remediation-list{margin:0;padding-left:18px;display:grid;gap:4px;font-size:12px}

.error-card{
  border:1px solid rgba(200,0,0,.2);
  border-radius:10px;
  padding:12px 14px;
  display:grid;
  gap:6px;
  background:rgba(200,0,0,.03);
}
.error-code{font-size:12px;font-weight:700;font-family:monospace}
.error-msg{margin:0;font-size:13px;line-height:1.5}
.next-action{font-size:12px}
.redacted-note{font-size:11px;opacity:.6;font-style:italic}

.artifact-card{
  border:1px solid rgba(0,0,0,.1);
  border-radius:10px;
  padding:10px 12px;
  display:grid;
  gap:6px;
}
.art-header{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.art-label{font-weight:600;font-size:13px}
.art-meta{display:flex;gap:6px;flex-wrap:wrap}
.art-history{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:11px}
.history-label{opacity:.65}
.history-pill{
  border:1px solid rgba(0,0,0,.1);
  border-radius:6px;
  padding:1px 6px;
  font-family:monospace;
  background:rgba(0,0,0,.03);
}
</style>
