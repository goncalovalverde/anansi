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
              <p class="chart-section-desc">Visualise how long items spent in flight and when they completed.</p>
            </div>
            <div class="chart-row-full">
              <ChartCard chart-id="chart-flow-timeline" title="Item Timeline (Gantt)" description="Each bar is one issue - from In Progress to Done. Long bars indicate slow-moving items." icon="📅" />
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
import StatusBar from '@/components/StatusBar.vue'
import ChartCard from '@/components/ChartCard.vue'

const store = useDataStore()
const loading = ref(false)
const error = ref(null)

const CHART_META = [
  { key: 'flow_efficiency', containerId: 'chart-flow-efficiency' },
  { key: 'wip_trend',       containerId: 'chart-flow-wip' },
  { key: 'throughput',      containerId: 'chart-flow-throughput' },
  { key: 'timeline',        containerId: 'chart-flow-timeline' },
  { key: 'distribution',    containerId: 'chart-flow-distribution' },
  { key: 'timeline_size',   containerId: 'chart-flow-timeline-size' },
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
  if (!charts || !window.Plotly) return
  const theme = getTheme()
  for (const { key, containerId } of CHART_META) {
    const el = document.getElementById(containerId)
    if (!el) continue
    if (!charts[key]) {
      el.innerHTML = '<div class="chart-placeholder"><span class="chart-placeholder-icon">📊</span><span>No data</span></div>'
      continue
    }
    const fig = charts[key]
    const titleText = (typeof fig.layout?.title === 'string' ? fig.layout.title : fig.layout?.title?.text) || ''
    const isError = titleText.includes('unavailable') || titleText.includes('failed') || titleText.includes('No completed')

    const calloutEl = el.parentElement?.querySelector('.chart-callout')
    if (isError) {
      el.innerHTML = `<div class="chart-empty-state"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg><span>This chart needs more data.</span></div>`
      if (calloutEl) calloutEl.style.display = 'none'
      continue
    }

    const layout = Object.assign({}, fig.layout || {}, theme)
    delete layout.title

    if (key === 'distribution' || key === 'timeline_size') {
      layout.xaxis = Object.assign({}, layout.xaxis || {}, { tickformat: '%b %Y', tickangle: -30 })
    }
    if (key === 'timeline') {
      layout.yaxis = Object.assign({}, layout.yaxis || {}, { automargin: true })
    }

    window.Plotly.newPlot(el, fig.data || [], layout, PLOTLY_CONFIG)
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
    renderCharts(charts)
  } catch (err) {
    error.value = `Failed to load flow charts: ${err.message}`
  } finally {
    loading.value = false
  }
}

watch(() => store.flowCharts, (charts) => {
  if (charts) renderCharts(charts)
})

onMounted(() => {
  if (store.flowCharts) {
    renderCharts(store.flowCharts)
  } else if (store.datasetId) {
    fetchAndRender()
  }
})
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
