<template>
  <main>
    <div class="container">

      <!-- Status bar -->
      <StatusBar />

      <!-- KPI strip -->
      <KpiStrip />

      <!-- Insight pills -->
      <InsightBar />

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
import { useDataLoader } from '@/composables/useDataLoader.js'
import { PLOTLY_CONFIG, EMPTY_PLACEHOLDER_HTML, ERROR_STATE_HTML, applyTheme, isErrorFigure, deferRender, plotChart } from '@/composables/useChartRenderer.js'
import StatusBar from '@/components/StatusBar.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import EmptyState from '@/components/EmptyState.vue'
import ChartCard from '@/components/ChartCard.vue'
import InsightBar from '@/components/InsightBar.vue'

const store = useDataStore()
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

function renderCharts(charts) {
  const HISTOGRAM_KEYS = ['pbis_created', 'pbis_done', 'type_issue']
  for (const { key, containerId } of CHART_META) {
    const el = document.getElementById(containerId)
    if (!el) continue
    const calloutEl = el.parentElement?.querySelector('.chart-callout')

    if (!charts[key]) {
      el.innerHTML = EMPTY_PLACEHOLDER_HTML
      if (calloutEl) calloutEl.style.display = 'none'
      continue
    }
    const fig = charts[key]
    const isEmpty = !fig.data || fig.data.length === 0 ||
      fig.data.every(t => !t.x || t.x.length === 0)

    if (key === 'story_points' && isEmpty) {
      el.innerHTML = `<div class="chart-placeholder">
        <span class="chart-placeholder-icon">📊</span>
        <span>Story points not tracked</span>
        <span class="chart-placeholder-hint">Your team may not use story points, or the field ID needs configuring.<br>
          <a href="#/config">Update Story Points Field ID →</a></span>
      </div>`
      if (calloutEl) calloutEl.style.display = 'none'
      continue
    }

    if (isErrorFigure(fig)) {
      el.innerHTML = ERROR_STATE_HTML
      if (calloutEl) calloutEl.style.display = 'none'
      continue
    }

    const layout = applyTheme(fig.layout, el)
    delete layout.title

    if (key === 'treemap') {
      layout.margin = { t: 8, r: 8, b: 8, l: 8 }
    } else if (key === 'story_points') {
      layout.margin = { ...layout.margin, r: 50, b: 70 }
    } else if (HISTOGRAM_KEYS.includes(key)) {
      layout.margin = { ...layout.margin, r: 50, b: 60 }
    }
    if (key === 'distribution' || key === 'timeline_size') {
      layout.xaxis = { ...layout.xaxis, tickformat: '%b %Y', tickangle: -30 }
    }
    if (key === 'timeline') {
      layout.yaxis = { ...layout.yaxis, automargin: true }
    }
    if (key === 'timeline_size') {
      layout.xaxis = { ...layout.xaxis, title: { text: 'Completion date' } }
      layout.yaxis = { ...layout.yaxis, title: { text: 'Cycle time (days)' } }
    }
    if (key === 'story_points') {
      layout.xaxis = { ...layout.xaxis, type: 'category', tickangle: -30, automargin: true }
    }

    plotChart(el, fig.data || [], layout, PLOTLY_CONFIG)

    const callout = (store.callouts || {})[key]
    if (calloutEl) {
      if (callout?.message) {
        calloutEl.textContent = callout.message
        calloutEl.className = `chart-callout callout-${callout.severity}`
        calloutEl.style.display = ''
      } else {
        calloutEl.style.display = 'none'
      }
    }
  }
}

function scheduleRender(charts) {
  deferRender(() => renderCharts(charts))
}

// Re-render when charts change (new data loaded)
watch(() => store.charts, (charts) => {
  if (charts) scheduleRender(charts)
})

onMounted(() => {
  if (store.datasetId) {
    loader.restore(store.datasetId)
  }
  if (store.charts) {
    scheduleRender(store.charts)
  }
})
</script>
