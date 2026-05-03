<template>
  <main>
    <div class="container">

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
          <div class="chart-row-half">
            <ChartCard ref="chartRefs[0]" chart-id="chart-treemap" title="Completed Work by Epic"
              description="What has been shipped? Drill into each Epic to see completed Stories and Bugs." icon="🗺" />
            <ChartCard ref="chartRefs[1]" chart-id="chart-pbis-created" title="New Issues Created Over Time"
              description="Is the backlog growing? Each bar shows new issues created per period, grouped by Epic." icon="📝" />
          </div>
          <div class="chart-row-full">
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
          <div class="chart-row-half">
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
          <div class="chart-row-full">
            <ChartCard ref="chartRefs[5]" chart-id="chart-timeline" title="Item Timeline (Gantt)"
              description="Each bar is one issue — from 'In Progress' to 'Done'. Long bars indicate slow-moving items." icon="📅" />
          </div>
          <div class="chart-row-full">
            <ChartCard ref="chartRefs[6]" chart-id="chart-distribution" title="Done vs In-Progress Date Spread"
              description="When did items transition? Clusters indicate sprint endings; gaps may reveal blocked periods." icon="📈" />
          </div>
          <div class="chart-row-full">
            <ChartCard ref="chartRefs[7]" chart-id="chart-timeline-size" title="Delivery Size Over Time"
              description="Bubble size = cycle time in days. Large bubbles done recently may indicate items that dragged on." icon="⏱" />
          </div>
        </section>

      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useDataStore } from '@/stores/data.js'
import { useConfigStore } from '@/stores/config.js'
import { useDataLoader } from '@/composables/useDataLoader.js'
import StatusBar from '@/components/StatusBar.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChartCard from '@/components/ChartCard.vue'

const store = useDataStore()
const configStore = useConfigStore()
const loader = useDataLoader()

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

function getTheme() {
  return {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter, Roboto, sans-serif', color: '#2C3E50', size: 12 },
    margin: { t: 16, r: 40, b: 40, l: 50 },
    colorway: ['#007B85','#F5A623','#D35400','#2C3E50','#5DADE2','#A569BD','#52BE80'],
    legend: { orientation: 'h', y: -0.15, xanchor: 'center', x: 0.5 },
    xaxis: { automargin: true },
    yaxis: { automargin: true },
  }
}

const PLOTLY_CONFIG = {
  displayModeBar: 'hover',
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['select2d','lasso2d','autoScale2d','toggleSpikelines','hoverClosestCartesian','hoverCompareCartesian'],
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

    // Detect error figures returned by Python (title contains error message)
    const titleText = (typeof fig.layout?.title === 'string' ? fig.layout.title :
      fig.layout?.title?.text) || ''
    const isError = titleText.includes('unavailable') || titleText.includes('failed') ||
      titleText.includes('No completed') || titleText.includes('needs more data')

    if (isError) {
      el.innerHTML = `
        <div class="chart-empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>This chart needs more data — try loading a wider date range or check your workflow configuration.</span>
          <a href="#/config" class="chart-empty-link">Go to Configuration →</a>
        </div>`
      continue
    }

    const layout = Object.assign({}, fig.layout || {}, theme)
    delete layout.title

    // Per-chart layout additions
    const HISTOGRAM_KEYS = ['pbis_created', 'pbis_done', 'story_points', 'type_issue']
    if (key === 'treemap') {
      layout.margin = { t: 8, r: 8, b: 8, l: 8 }
    } else if (HISTOGRAM_KEYS.includes(key)) {
      layout.margin = Object.assign({}, layout.margin, { r: 50, b: 60 })
    }
    if (key === 'distribution' || key === 'timeline_size') {
      layout.xaxis = Object.assign({}, layout.xaxis || {}, { tickformat: '%b %Y', tickangle: -30 })
    }
    if (key === 'timeline') {
      layout.yaxis = Object.assign({}, layout.yaxis || {}, { automargin: true })
    }
    if (key === 'timeline_size') {
      layout.xaxis = Object.assign({}, layout.xaxis || {}, { title: { text: 'Completion date' } })
      layout.yaxis = Object.assign({}, layout.yaxis || {}, { title: { text: 'Cycle time (days)' } })
    }
    if (key === 'story_points') {
      layout.xaxis = Object.assign({}, layout.xaxis || {}, { type: 'category', tickangle: -30, automargin: true })
    }

    window.Plotly.newPlot(el, fig.data || [], layout, PLOTLY_CONFIG)
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
