<template>
  <main>
    <div class="container">
      <StatusBar />

      <div v-if="!store.datasetId" class="empty-state">
        <p>No dataset loaded. Go to <router-link to="/config">Configuration</router-link> to load data.</p>
      </div>

      <template v-else>
        <div class="trends-note">
          Trends always show the full available date range.
        </div>

        <div v-if="loading" class="trends-loading">Loading trend charts...</div>
        <div v-else-if="error" class="trends-error">{{ error }}</div>

        <div v-show="store.trendsCharts">
          <section class="chart-section" aria-labelledby="section-trends-cumulative">
            <div class="chart-section-header">
              <h2 class="chart-section-title" id="section-trends-cumulative">Cumulative Flow</h2>
              <p class="chart-section-desc">Track how work items accumulate over time - the gap between created and completed shows work in progress.</p>
            </div>
            <div class="chart-row-full">
              <ChartCard chart-id="chart-trends-cumulative" title="Cumulative Flow Diagram" description="Items created vs completed over time. Narrowing gap means the team is catching up." icon="📈" />
            </div>
          </section>

          <section class="chart-section" aria-labelledby="section-trends-delivery">
            <div class="chart-section-header">
              <h2 class="chart-section-title" id="section-trends-delivery">Delivery Trends</h2>
              <p class="chart-section-desc">Monthly completion rates and epic-level progress over time.</p>
            </div>
            <div class="chart-row-half">
              <ChartCard chart-id="chart-trends-monthly" title="Monthly Throughput" description="Items completed per month with trend line. Upward trend indicates improving delivery pace." icon="📅" />
              <ChartCard chart-id="chart-trends-epic-progress" title="Epic Progress Timeline" description="When did each epic deliver its first and last items? Shows epic lifecycle duration." icon="🗺" />
            </div>
          </section>
        </div>
      </template>
    </div>
  </main>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useDataStore } from '@/stores/data.js'
import { Api } from '@/api/index.js'
import StatusBar from '@/components/StatusBar.vue'
import ChartCard from '@/components/ChartCard.vue'

const store = useDataStore()
const loading = ref(false)
const error = ref(null)

const CHART_META = [
  { key: 'cumulative_flow',    containerId: 'chart-trends-cumulative' },
  { key: 'monthly_throughput', containerId: 'chart-trends-monthly' },
  { key: 'epic_progress',      containerId: 'chart-trends-epic-progress' },
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

    const figLayout = fig.layout || {}
    const layout = {
      ...figLayout,
      paper_bgcolor: theme.paper_bgcolor,
      plot_bgcolor:  theme.plot_bgcolor,
      font:          theme.font,
      colorway:      theme.colorway,
      margin:  { ...(figLayout.margin || {}), ...theme.margin },
      legend:  { ...(figLayout.legend || {}), ...theme.legend },
      xaxis:   { ...(figLayout.xaxis  || {}), ...(theme.xaxis  || {}) },
      yaxis:   { ...(figLayout.yaxis  || {}), ...(theme.yaxis  || {}) },
    }
    delete layout.title

    if (key === 'epic_progress') {
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
    const charts = await Api.getTrends(store.datasetId)
    store.setTrendsCharts(charts)
    scheduleRender(charts)
  } catch (err) {
    error.value = `Failed to load trend charts: ${err.message}`
  } finally {
    loading.value = false
  }
}

watch(() => store.trendsCharts, (charts) => {
  if (charts) scheduleRender(charts)
})

onMounted(() => {
  if (store.trendsCharts) {
    scheduleRender(store.trendsCharts)
  } else if (store.datasetId) {
    fetchAndRender()
  }
})

function scheduleRender(charts) {
  nextTick(() => requestAnimationFrame(() => renderCharts(charts)))
}
</script>

<style scoped>
.trends-note {
  background: var(--accent-light);
  color: var(--text-secondary);
  border-radius: var(--radius);
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}
.trends-loading, .trends-error {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
.trends-error { color: var(--danger); }
.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
</style>
