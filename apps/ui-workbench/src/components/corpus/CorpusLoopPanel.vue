<script setup lang="ts">
import { corpusLoopV1 } from '../../generated/corpusLoopV1'

const shortCommit = (sha: string) => sha.slice(0, 8)
</script>

<template>
  <section class="corpus-panel" aria-labelledby="corpus-loop-title">
    <div class="corpus-kicker">Watson / Cyc / Semantic Web / CHRONOS</div>
    <h2 id="corpus-loop-title">Corpus loop v1 coordination</h2>
    <p class="corpus-summary">
      Read-only SocioSphere coordination view for the five pinned carrier surfaces.
      SocioSphere records topology and validation status; each downstream repo owns its own carrier.
    </p>

    <div class="corpus-meta">
      <span>Source corpus: <strong>{{ corpusLoopV1.sourceCorpus }}</strong></span>
      <span>Validation: <code>{{ corpusLoopV1.validationTarget }}</code></span>
      <span class="boundary">{{ corpusLoopV1.status }}</span>
    </div>

    <div class="component-grid">
      <article v-for="item in corpusLoopV1.components" :key="item.repo" class="component-card">
        <div class="component-plane">{{ item.plane }}</div>
        <div class="component-repo">{{ item.repo }}</div>
        <div class="component-artifact">{{ item.artifact }}</div>
        <div class="component-merge">Merged {{ item.merged }} · {{ shortCommit(item.commit) }}</div>
      </article>
    </div>

    <div class="acceptance-grid">
      <section>
        <h3>Positive checks</h3>
        <ul>
          <li v-for="item in corpusLoopV1.positive" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section>
        <h3>Negative checks</h3>
        <ul>
          <li v-for="item in corpusLoopV1.negative" :key="item">{{ item }}</li>
        </ul>
      </section>
    </div>
  </section>
</template>

<style scoped>
.corpus-panel{
  margin:32px auto 96px;
  padding:24px;
  max-width:1100px;
  border:1px solid rgba(255,255,255,.12);
  border-radius:18px;
  background:rgba(255,255,255,.04);
  text-align:left;
}
.corpus-kicker{
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.12em;
  opacity:.68;
  font-weight:700;
}
h2{margin:8px 0 8px;font-size:28px;line-height:1.15}
.corpus-summary{max-width:820px;opacity:.8;margin:0 0 18px}
.corpus-meta{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.corpus-meta span{border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:6px 10px;font-size:13px;background:rgba(0,0,0,.12)}
.boundary{font-weight:700}
.component-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:20px}
.component-card{border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:14px;background:rgba(0,0,0,.16)}
.component-plane{font-size:12px;text-transform:uppercase;letter-spacing:.08em;opacity:.65;font-weight:700}
.component-repo{font-weight:700;margin-top:6px;font-size:14px}
.component-artifact{opacity:.78;font-size:13px;margin-top:6px}
.component-merge{font-size:12px;margin-top:12px;opacity:.64}
.acceptance-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
h3{margin:0 0 8px;font-size:16px}
ul{margin:0;padding-left:20px;opacity:.84}
li{margin:4px 0}
@media (prefers-color-scheme: light){
  .corpus-panel{border-color:rgba(0,0,0,.12);background:rgba(0,0,0,.03)}
  .corpus-meta span,.component-card{border-color:rgba(0,0,0,.12);background:rgba(255,255,255,.8)}
}
</style>
