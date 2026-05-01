<template>
  <div class="status-bar" role="status" aria-live="polite">
    <div :class="['status-indicator', store.status]"></div>
    <span class="status-text">{{ store.statusText }}</span>
    <span class="status-detail">{{ store.statusDetail }}</span>
  </div>
</template>

<script setup>
import { useDataStore } from '@/stores/data.js'
const store = useDataStore()
</script>
