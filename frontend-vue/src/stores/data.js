import { defineStore } from 'pinia'

const STORAGE_KEY    = 'anansi_last_dataset_id'
const STORAGE_LOADED = 'anansi_last_loaded_ts'

export const useDataStore = defineStore('data', {
  state: () => ({
    datasetId:   localStorage.getItem(STORAGE_KEY) || null,
    lastLoadedTs: parseInt(localStorage.getItem(STORAGE_LOADED) || '0', 10) || null,
    status: 'idle',       // idle | loading | ready | error
    statusText: 'Idle — click "Load Data" to begin',
    statusDetail: '',
    isLoading: false,
    charts: null,
    kpis: null,
    hasData: false,
  }),
  actions: {
    setStatus(state, text, detail = '') {
      this.status = state
      this.statusText = text
      this.statusDetail = detail
    },
    setLoading(v) { this.isLoading = v },
    setCharts(charts, datasetId, saveTimestamp) {
      this.charts = charts
      this.kpis = charts.kpis || null
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
      this.hasData = false
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(STORAGE_LOADED)
    },
  },
})
