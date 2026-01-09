<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const seedId = computed(() => String(route.params.id ?? 'demo'))
</script>

<template>
  <div class="page">
    <h2>Graph</h2>
    <div class="card">Stub graph for: {{ seedId }}</div>
  </div>
</template>

<style scoped>
.page{display:grid;gap:12px;padding:18px}
.card{border:1px solid rgba(0,0,0,.12);border-radius:14px;padding:12px 14px}
</style>
