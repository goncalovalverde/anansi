<template>
  <main>
    <div class="container">

      <!-- Toolbar -->
      <div class="toolbar">
        <button class="btn btn-primary" :disabled="store.isLoading" @click="loader.load(false)">
          {{ store.isLoading ? 'Loading…' : '⬇ Load Data' }}
        </button>
        <button class="btn btn-secondary" :disabled="store.isLoading" @click="refresh" title="Re-fetch data from Jira">↺ Refresh</button>
        <button class="btn btn-danger" @click="handleClearCache">🗑 Clear Cache</button>
        <span class="toolbar-spacer"></span>
        <div v-if="store.hasData" class="date-range-control">
          <span class="date-range-label">Show:</span>
          <div class="date-range-btns" role="group" aria-label="Date range filter">
            <button v-for="d in [30, 60, 90, 0]" :key="d"
              :class="['date-range-btn', { active: activeDays === d }]"
              @click="applyDateRange(d)">{{ d === 0 ? 'All' : d + 'd' }}</button>
          </div>
        </div>
        <span class="toolbar-spacer"></span>
        <span v-if="lastLoadedLabel" class="last-loaded-info">{{ lastLoadedLabel }}</span>
      </div>

      <!-- Status bar -->
      <StatusBar />

      <!-- KPI strip -->
      <KpiStrip />

      <!-- Empty state -->
      <EmptyState v-if="!store.hasData" @load="loader.load(false)" />

      <!-- Chart sections -->
      <div v-show="store.hasData">

        <!-- Section 1: Backlog Composition -->
        <section class="chart-section" aria-labelledby="section-backlog">
          <div class="chart-section-header">
            <h2 class="chart-section-title" id="section-backlog">📦 Backlog Composition</h2>
            <p class="chart-section-desc">Understand what work exists, how it is structured across Epics, and what types of issues dominate the backlog.</p>
          </div>
          <div class="charts-grid">
            <ChartCard ref="chartRefs[0]" chart-id="chart-treemap" title="Completed Work by Epic"
              description="What has been shipped? Drill into each Epic to see completed Stories and Bugs." icon="🗺" />
            <ChartCard ref="chartRefs[1]" chart-id="chart-pbis-created" title="New Issues Created Over Time"
              description="Is the backlog growing? Each bar shows new issues created per period, grouped by Epic." icon="📝" />
            <ChartCard ref="chartRefs[2]" chart-id="chart-type-issue" title="Work Mix by Type"
              description="What proportion is Stories vs Bugs vs Tasks? A high bug ratio signals quality issues." icon="🏷" />
          </div>
        </section>

        <!-- Section 2: Delivery Pace -->
        <section class="chart-section" aria-labelledby="section-delivery">
          <div class="chart-section-header">
            <h2 class="chart-section-title" id="section-delivery">🚀 Delivery Pace</h2>
            <p class="chart-section-desc">Track how much work is being completed and the story point velocity broken down by Epic.</p>
          </div>
          <div class="charts-grid">
            <ChartCard ref="chartRefs[3]" chart-id="chart-pbis-done" title="Completed Issues Over Time"
              description="When were items marked Done? Use this to spot sprint completion patterns or dry spells." icon="✅" />
            <ChartCard ref="chartRefs[4]" chart-id="chart-story-points" title="Story Points Delivered"
              description="How many story points were delivered per Epic? Compare effort investment across product areas." icon="📊" />
          </div>
        </section>

        <!-- Section 3: Flow & Cycle Time -->
        <section class="chart-section" aria-labelledby="section-flow">
          <div class="chart-section-header">
            <h2 class="chart-section-title" id="section-flow">⏱ Flow &amp; Cycle Time</h2>
            <p class="chart-section-desc">Measure how long work takes from start to finish and identify bottlenecks or outliers slowing delivery.</p>
          </div>
          <div class="charts-grid">
            <ChartCard ref="chartRefs[5]" chart-id="chart-timeline" title="Item Timeline (Gantt)"
              description="Each bar is one issue — from 'In Progress' to 'Done'. Long bars indicate slow-moving items." icon="📅" />
            <ChartCard ref="chartRefs[6]" chart-id="chart-distribution" title="Done vs In-Progress Date Spread"
              description="When did items transition? Clusters indicate sprint endings; gaps may reveal blocked periods." icon="📈" />
            <ChartCard ref="chartRefs[7]" chart-id="chart-timeline-size" title="Delivery Size Over Time"
              description="Bubble size = cycle time in days. Large bubbles done recently may indicate items that dragged on." icon="⏱" />
          </div>
        </section>

      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from 'vue'
import { useDataStore } from '@/stores/data.js'
import { useConfigStore } from '@/stores/config.js'
import { useDataLoader } from '@/composables/useDataLoader.js'
import { Api } from '@/api/index.js'
import StatusBar from '@/components/StatusBar.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChartCard from '@/components/ChartCard.vue'

const store = useDataStore()
const configStore = useConfigStore()
const loader = useDataLoader()
const showNotification = inject('showNotification')

const activeDays = ref(30)
const chartRefs = ref([])

// Chart metadata — order matches ChartCard refs above
const CHART_META = [
  { key: 'treemap',       containerId: 'chart-treemap' },
  { key: 'pbis_created',  containerId: 'chart-pbis-created' },
  { key: 'type_issue',    containerId: 'chart-type-issue' },
  { key: 'pbis_done',     containerId: 'chart-pbis-done' },
  { key: 'story_points',  containerId: 'chart-story-points' },
  { key: 'timeline',      containerId: 'chart-timeline' },
  { key: 'distribution',  containerId: 'chart-distribution' },
  { key: 'timeline_size', containerId: 'chart-timeline-size' },
]

const lastLoadedLabel = computed(() => {
  if (!store.lastLoadedTs) return ''
  const d = new Date(store.lastLoadedTs)
  return `Last loaded: ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ${d.toLocaleDateString()}`
})

function getTheme() {
  const isLight = configStore.theme === 'light'
  return {
    paper_bgcolor: isLight ? '#ffffff' : '#1e2130',
    plot_bgcolor:  isLight ? '#f5f6fa' : '#1e2130',
    font:   { color: isLight ? '#1a1d27' : '#e8eaf0', size: 11 },
    margin: { t: 40, b: 40, l: 40, r: 20 },
  }
}

function renderCharts(charts) {
  const theme = getTheme()
  for (const { key, containerId } of CHART_META) {
    const el = document.getElementById(containerId)
    if (!el) continue
    if (!charts[key]) {
      el.innerHTML = '<div class="chart-placeholder"><span class="chart-placeholder-icon">📊</span><span>No data</span></div>'
      continue
    }
    const fig = charts[key]
    const isEmpty = !fig.data || fig.data.length === 0 ||
      (fig.data[0] && (!fig.data[0].x || fig.data[0].x.length === 0))

    if (key === 'story_points' && isEmpty) {
      el.innerHTML = `<div class="chart-placeholder">
        <span class="chart-placeholder-icon">📊</span>
        <span>Story points not tracked</span>
        <span class="chart-placeholder-hint">Your team may not use story points, or the field ID needs configuring.<br>
          <a href="#/config">Update Story Points Field ID →</a></span>
      </div>`
      continue
    }
    const layout = Object.assign({}, fig.layout || {}, {
      paper_bgcolor: theme.paper_bgcolor,
      plot_bgcolor:  theme.plot_bgcolor,
      font:   theme.font,
      margin: theme.margin,
    })
    window.Plotly.newPlot(el, fig.data || [], layout, { responsive: true, displaylogo: false })
  }
}

// Re-render when charts change (new data loaded)
watch(() => store.charts, (charts) => {
  if (charts) renderCharts(charts)
})

// Re-render when theme changes (no network call)
watch(() => configStore.theme, () => {
  if (store.charts) renderCharts(store.charts)
})

function applyDateRange(days) {
  activeDays.value = days
  for (const { containerId } of CHART_META) {
    const el = document.getElementById(containerId)
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

onMounted(() => {
  if (store.datasetId) {
    loader.restore(store.datasetId)
  }
  // If charts already in store (e.g. navigating back from config), re-render immediately
  if (store.charts) {
    renderCharts(store.charts)
  }
})
</script>
