<script setup lang="ts">
import type { OperationEvent } from '../../schemas/operation'

defineProps<{ events: OperationEvent[] }>()

const stageIcon: Record<string, string> = {
  pending: '○',
  running: '◑',
  'waiting-decision': '◈',
  blocked: '⊗',
  completed: '●',
  cancelled: '⊘',
  failed: '✕',
}
</script>

<template>
  <section class="activity-feed" aria-label="Operation activity feed">
    <h3 class="feed-title">Activity</h3>
    <ol class="feed-list" v-if="events.length">
      <li
        v-for="ev in [...events].reverse()"
        :key="ev.eventId"
        class="feed-item"
        :data-stage="ev.stage"
      >
        <span class="icon" aria-hidden="true">{{ stageIcon[ev.stage] ?? '·' }}</span>
        <span class="sr-only">Stage: {{ ev.stage }}</span>
        <div class="item-body">
          <div class="stage-row">
            <span class="stage-text">{{ ev.stage }}</span>
            <time class="ts" :datetime="ev.ts">{{ new Date(ev.ts).toLocaleString() }}</time>
          </div>
          <div v-if="ev.detail" class="detail">{{ ev.detail }}</div>
        </div>
      </li>
    </ol>
    <p v-else class="empty">No events recorded.</p>
  </section>
</template>

<style scoped>
.activity-feed{display:grid;gap:8px}
.feed-title{margin:0;font-size:13px;text-transform:uppercase;letter-spacing:.07em;opacity:.65;font-weight:600}
.feed-list{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.feed-item{
  display:flex;
  gap:10px;
  align-items:flex-start;
  padding:8px 10px;
  border-radius:10px;
  background:rgba(0,0,0,.02);
  border:1px solid rgba(0,0,0,.07);
}
.feed-item[data-stage="completed"]{background:rgba(0,120,0,.04);border-color:rgba(0,120,0,.14)}
.feed-item[data-stage="failed"]{background:rgba(200,0,0,.03);border-color:rgba(200,0,0,.12)}
.feed-item[data-stage="blocked"]{background:rgba(200,100,0,.04);border-color:rgba(200,100,0,.14)}
.feed-item[data-stage="waiting-decision"]{background:rgba(0,60,200,.03);border-color:rgba(0,60,200,.12)}
.icon{font-size:15px;flex-shrink:0;margin-top:1px;font-variant-emoji:text}
.item-body{display:grid;gap:2px;flex:1;min-width:0}
.stage-row{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.stage-text{font-size:12px;font-weight:600;text-transform:lowercase}
.ts{font-size:11px;opacity:.6;flex-shrink:0}
.detail{font-size:12px;opacity:.8;word-break:break-word}
.empty{font-size:13px;opacity:.6;margin:0}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
</style>
