<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const type = computed(() => String(route.params.type ?? 'unknown'))
const id = computed(() => String(route.params.id ?? 'unknown'))
</script>

<template>
  <div class="page">
    <h2>Entity</h2>
    <div class="card">{{ type }} / {{ id }}</div>
  </div>
</template>

<style scoped>
.page{display:grid;gap:12px;padding:18px}
.card{border:1px solid rgba(0,0,0,.12);border-radius:14px;padding:12px 14px}
</style>
