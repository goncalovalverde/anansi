<template>
  <div class="app-topbar">
    <!-- Page title -->
    <h1 class="topbar-title">{{ pageTitle }}</h1>

    <!-- Dashboard actions (only on Dashboard) -->
    <div v-if="route.path === '/'" class="topbar-actions">
      <button class="btn btn-primary btn-sm" :disabled="store.isLoading" @click="loader.load(false)">
        {{ store.isLoading ? 'Loading…' : '⬇ Load Data' }}
      </button>
      <button class="btn btn-secondary btn-sm" :disabled="store.isLoading" @click="refresh" title="Re-fetch data from Jira">↺ Refresh</button>
      <button class="btn btn-danger btn-sm" @click="handleClearCache">🗑 Clear Cache</button>
    </div>

    <!-- Right: date range + last loaded (only on Dashboard, only when data exists) -->
    <div v-if="route.path === '/'" class="topbar-right">
      <template v-if="store.hasData">
        <span class="date-range-label">Show:</span>
        <div class="date-range-btns" role="group" aria-label="Date range filter">
          <button v-for="d in [30, 60, 90, 0]" :key="d"
            :class="['date-range-btn', { active: activeDays === d }]"
            @click="applyDateRange(d)">{{ d === 0 ? 'All' : d + 'd' }}</button>
        </div>
      </template>
      <span v-if="lastLoadedLabel" class="last-loaded-info">{{ lastLoadedLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useDataStore } from '@/stores/data.js'
import { useDataLoader } from '@/composables/useDataLoader.js'
import { Api } from '@/api/index.js'

const route = useRoute()
const store = useDataStore()
const loader = useDataLoader()
const showNotification = inject('showNotification')

const activeDays = ref(30)

const CHART_IDS = [
  'chart-treemap',
  'chart-pbis-created',
  'chart-type-issue',
  'chart-pbis-done',
  'chart-story-points',
  'chart-timeline',
  'chart-distribution',
  'chart-timeline-size',
]

const pageTitle = computed(() => {
  if (route.path === '/') return 'Dashboard'
  if (route.path === '/config') return 'Configuration'
  return 'Anansi'
})

const lastLoadedLabel = computed(() => {
  if (!store.lastLoadedTs) return ''
  const d = new Date(store.lastLoadedTs)
  return `Last loaded: ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ${d.toLocaleDateString()}`
})

function applyDateRange(days) {
  activeDays.value = days
  for (const id of CHART_IDS) {
    const el = document.getElementById(id)
    if (!el || !el._fullLayout) continue
    if (days === 0) {
      window.Plotly.relayout(el, { 'xaxis.autorange': true })
    } else {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - days)
      window.Plotly.relayout(el, { 'xaxis.range': [start.toISOString(), end.toISOString()] })
    }
  }
}

async function refresh() {
  if (confirm('Re-fetch fresh data from Jira? This will bypass the cache.')) loader.load(true)
}

async function handleClearCache() {
  if (!confirm('Delete all cached datasets? This cannot be undone.')) return
  loader.stop()
  try {
    const { deleted } = await Api.clearCache()
    store.clearData()
    store.setStatus('idle', 'Cache cleared', `Removed ${deleted} dataset(s)`)
    showNotification?.(`Cleared ${deleted} cached dataset(s)`, 'info')
  } catch (err) {
    showNotification?.('Failed to clear cache: ' + err.message, 'error')
  }
}
</script>
