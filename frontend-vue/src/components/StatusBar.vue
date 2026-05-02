<template>
  <div class="status-bar" role="status" aria-live="polite">
    <div :class="['status-indicator', store.status]"></div>
    <div class="status-bar-content">
      <div class="status-texts">
        <span class="status-text">{{ store.statusText }}</span>
        <span class="status-detail">{{ store.statusDetail }}</span>
      </div>
      <div v-if="showProgress" class="progress-container" aria-label="Loading progress">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
        <span class="progress-label">{{ store.progress.loaded }} / {{ store.progress.total }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDataStore } from '@/stores/data.js'
const store = useDataStore()

const showProgress = computed(() =>
  store.status === 'loading' && store.progress.total > 0
)
const progressPct = computed(() => {
  const { loaded, total } = store.progress
  if (!total) return 0
  return Math.min(100, Math.round((loaded / total) * 100))
})
</script>
