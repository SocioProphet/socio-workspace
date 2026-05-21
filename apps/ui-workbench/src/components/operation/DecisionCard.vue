<script setup lang="ts">
import { computed } from 'vue'
import type { DecisionCard } from '../../schemas/operation'

const props = defineProps<{ decision: DecisionCard }>()
const emit = defineEmits<{ (e: 'choose', optionId: string): void }>()

const resolved = computed(() => props.decision.chosenOptionId !== null)

function choose(optionId: string) {
  if (!resolved.value) emit('choose', optionId)
}
</script>

<template>
  <div
    class="decision-card"
    :data-type="decision.type"
    :data-resolved="resolved"
    role="group"
    :aria-label="`Decision: ${decision.type}`"
  >
    <div class="header">
      <span class="type-badge">{{ decision.type }}</span>
      <span v-if="resolved" class="resolved-badge" aria-label="Decision resolved">resolved</span>
    </div>

    <p class="prompt">{{ decision.prompt }}</p>

    <div class="actor-line">
      <span class="actor-label">Responsible actor:</span>
      <span class="actor">{{ decision.responsibleActor }}</span>
    </div>

    <div class="options" role="group" aria-label="Decision options">
      <button
        v-for="opt in decision.options"
        :key="opt.id"
        class="opt-btn"
        :class="{ chosen: decision.chosenOptionId === opt.id, destructive: opt.destructive }"
        :disabled="resolved"
        :aria-pressed="decision.chosenOptionId === opt.id"
        @click="choose(opt.id)"
      >
        <span class="opt-label">{{ opt.label }}</span>
        <span v-if="opt.description" class="opt-desc">{{ opt.description }}</span>
      </button>
    </div>

    <div v-if="resolved" class="resolution-note">
      Resolved: option <strong>{{ decision.chosenOptionId }}</strong>
      <span v-if="decision.resolvedAt" class="ts">at {{ new Date(decision.resolvedAt).toLocaleString() }}</span>
    </div>
  </div>
</template>

<style scoped>
.decision-card{
  border:1px solid rgba(0,0,0,.14);
  border-radius:14px;
  padding:14px 16px;
  display:grid;
  gap:10px;
  background:rgba(0,0,0,.015);
}
.decision-card[data-resolved="true"]{
  opacity:.75;
}
.header{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.type-badge{
  font-size:11px;
  border:1px solid rgba(0,0,0,.15);
  border-radius:999px;
  padding:2px 8px;
  text-transform:uppercase;
  letter-spacing:.06em;
  font-weight:600;
}
.resolved-badge{
  font-size:11px;
  border:1px solid rgba(0,120,0,.3);
  background:rgba(0,120,0,.07);
  border-radius:999px;
  padding:2px 8px;
  color:rgb(0,100,0);
}
.prompt{margin:0;font-weight:500}
.actor-line{display:flex;gap:6px;font-size:12px;opacity:.8}
.actor-label{font-weight:600}
.options{display:flex;gap:8px;flex-wrap:wrap}
.opt-btn{
  display:grid;
  gap:2px;
  border:1px solid rgba(0,0,0,.18);
  border-radius:10px;
  padding:8px 12px;
  background:rgba(255,255,255,.7);
  cursor:pointer;
  text-align:left;
}
.opt-btn:disabled{cursor:default;opacity:.6}
.opt-btn.chosen{border-color:rgba(0,90,200,.5);background:rgba(0,90,200,.07)}
.opt-btn.destructive{border-color:rgba(200,0,0,.3)}
.opt-btn.destructive:not(:disabled):hover{background:rgba(200,0,0,.07)}
.opt-label{font-size:13px;font-weight:600}
.opt-desc{font-size:11px;opacity:.75}
.resolution-note{font-size:12px;opacity:.8}
.ts{opacity:.65;margin-left:4px}
</style>
