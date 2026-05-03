import { defineStore } from 'pinia'

const STORAGE_KEY    = 'anansi_last_dataset_id'
const STORAGE_LOADED = 'anansi_last_loaded_ts'

export const useDataStore = defineStore('data', {
  state: () => {
    const storedId = localStorage.getItem(STORAGE_KEY)
    const datasetId = storedId && storedId !== 'undefined' && storedId !== 'null' ? storedId : null
    if (!datasetId && storedId) {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(STORAGE_LOADED)
    }
    return {
      datasetId,
      lastLoadedTs: parseInt(localStorage.getItem(STORAGE_LOADED) || '0', 10) || null,
      status: 'idle',
      statusText: 'Idle — click "Load Data" to begin',
      statusDetail: '',
      isLoading: false,
      charts: null,
      kpis: null,
      hasData: false,
      insights: null,
      callouts: null,
      flowCharts: null,
      trendsCharts: null,
      progress: { loaded: 0, total: 0 },
    }
  },
  actions: {
    setStatus(state, text, detail = '') {
      this.status = state
      this.statusText = text
      this.statusDetail = detail
    },
    setLoading(v) { this.isLoading = v },
    setProgress(loaded, total) { this.progress = { loaded, total } },
    setInsights(data) { this.insights = data },
    setFlowCharts(data) { this.flowCharts = data },
    setTrendsCharts(data) { this.trendsCharts = data },
    setCharts(charts, datasetId, saveTimestamp) {
      this.charts = charts
      this.kpis = charts.kpis || null
      this.callouts = charts.callouts || null
      this.datasetId = datasetId
      this.hasData = true
      if (saveTimestamp) {
        this.lastLoadedTs = Date.now()
        localStorage.setItem(STORAGE_KEY, datasetId)
        localStorage.setItem(STORAGE_LOADED, this.lastLoadedTs.toString())
      }
    },
    clearData() {
      this.datasetId = null
      this.lastLoadedTs = null
      this.charts = null
      this.kpis = null
      this.insights = null
      this.callouts = null
      this.flowCharts = null
      this.trendsCharts = null
      this.hasData = false
      this.progress = { loaded: 0, total: 0 }
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(STORAGE_LOADED)
    },
  },
})
