<template>
  <main>
    <div class="container">
      <StatusBar />

      <div v-if="!store.datasetId" class="empty-state">
        <p>No dataset loaded. Go to <router-link to="/config">Configuration</router-link> to load data.</p>
      </div>

      <template v-else>
        <div class="flow-note">
          Showing flow metrics for the loaded dataset. Load data from the <router-link to="/config">Configuration page</router-link> to update.
        </div>

        <div v-if="loading" class="flow-loading">Loading flow charts...</div>
        <div v-else-if="error" class="flow-error">{{ error }}</div>

        <div v-show="store.flowCharts">
          <section class="chart-section" aria-labelledby="section-flow-metrics">
            <div class="chart-section-header">
              <h2 class="chart-section-title" id="section-flow-metrics">Flow Metrics</h2>
              <p class="chart-section-desc">Track flow efficiency, WIP trend, and throughput over time.</p>
            </div>
            <div class="chart-row-third">
              <ChartCard chart-id="chart-flow-efficiency" title="Flow Efficiency" description="Ratio of completed items to all active items - higher is better." icon="⚡" />
              <ChartCard chart-id="chart-flow-wip" title="WIP Trend" description="Items in progress each week. Spikes indicate bottlenecks." icon="📈" />
              <ChartCard chart-id="chart-flow-throughput" title="Weekly Throughput" description="Items completed per week with 4-week rolling average." icon="🚀" />
            </div>
          </section>

          <section class="chart-section" aria-labelledby="section-flow-timeline">
            <div class="chart-section-header">
              <h2 class="chart-section-title" id="section-flow-timeline">Item Timelines</h2>
              <p class="chart-section-desc">Visualise when items completed and cycle time distribution.</p>
            </div>
            <div class="chart-row-full">
              <ChartCard chart-id="chart-flow-distribution" title="Done vs In-Progress Date Spread" description="When did items transition? Clusters indicate sprint endings." icon="📊" />
            </div>
            <div class="chart-row-full">
              <ChartCard chart-id="chart-flow-timeline-size" title="Delivery Size Over Time" description="Bubble size = cycle time in days. Large bubbles done recently may indicate items that dragged on." icon="⏱" />
            </div>
          </section>
        </div>
      </template>
    </div>
  </main>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useDataStore } from '@/stores/data.js'
import { Api } from '@/api/index.js'
import { PLOTLY_CONFIG, EMPTY_PLACEHOLDER_HTML, ERROR_STATE_HTML, applyTheme, isErrorFigure, deferRender, plotChart } from '@/composables/useChartRenderer.js'
import StatusBar from '@/components/StatusBar.vue'
import ChartCard from '@/components/ChartCard.vue'

const store = useDataStore()
const loading = ref(false)
const error = ref(null)

const CHART_META = [
  { key: 'flow_efficiency', containerId: 'chart-flow-efficiency' },
  { key: 'wip_trend',       containerId: 'chart-flow-wip' },
  { key: 'throughput',      containerId: 'chart-flow-throughput' },
  { key: 'distribution',    containerId: 'chart-flow-distribution' },
  { key: 'timeline_size',   containerId: 'chart-flow-timeline-size' },
]

function renderCharts(charts) {
  if (!charts || !window.Plotly) return
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
    if (isErrorFigure(fig)) {
      el.innerHTML = ERROR_STATE_HTML
      if (calloutEl) calloutEl.style.display = 'none'
      continue
    }

    const layout = applyTheme(fig.layout, el)
    delete layout.title

    if (key === 'distribution') {
      layout.xaxis = { ...layout.xaxis, tickformat: '%b %Y', tickangle: -30 }
    }
    if (key === 'timeline_size') {
      layout.xaxis = { ...layout.xaxis, tickformat: '%b %Y', tickangle: -30, title: { text: 'Completion date' } }
      layout.yaxis = { ...layout.yaxis, title: { text: 'Cycle Time' }, showticklabels: false }
    }

    plotChart(el, fig.data || [], layout, PLOTLY_CONFIG)
    if (calloutEl) calloutEl.style.display = 'none'
  }
}

async function fetchAndRender() {
  if (!store.datasetId) return
  loading.value = true
  error.value = null
  try {
    const charts = await Api.getFlow(store.datasetId)
    store.setFlowCharts(charts)
    scheduleRender(charts)
  } catch (err) {
    error.value = `Failed to load flow charts: ${err.message}`
  } finally {
    loading.value = false
  }
}

watch(() => store.flowCharts, (charts) => {
  if (charts) scheduleRender(charts)
})

onMounted(() => {
  if (store.flowCharts) {
    scheduleRender(store.flowCharts)
  } else if (store.datasetId) {
    fetchAndRender()
  }
})

function scheduleRender(charts) {
  deferRender(() => renderCharts(charts))
}
</script>

<style scoped>
.flow-note {
  background: var(--accent-light);
  color: var(--text-secondary);
  border-radius: var(--radius);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}
.flow-loading, .flow-error {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
.flow-error { color: var(--danger); }
.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
</style>
