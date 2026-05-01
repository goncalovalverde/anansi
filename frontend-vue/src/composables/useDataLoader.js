import { Api } from '@/api/index.js'
import { useDataStore } from '@/stores/data.js'

const POLL_MS = 2000

export function useDataLoader() {
  const store = useDataStore()
  let pollTimer = null
  let generation = 0

  function stop() {
    generation++
    clearInterval(pollTimer)
    pollTimer = null
  }

  async function load(forceRefresh = false) {
    stop()
    const gen = generation
    store.setLoading(true)
    store.setStatus('loading', 'Initiating data load…')

    try {
      const { dataset_id, cached } = await Api.loadData()
      if (gen !== generation) return

      if (cached && !forceRefresh) {
        store.setStatus('loading', 'Using cached dataset…')
        await _render(dataset_id, true, gen)
      } else {
        store.setStatus('loading', 'Fetching data from Jira…', 'This may take a while for large projects')
        _poll(dataset_id, gen)
      }
    } catch (err) {
      if (gen !== generation) return
      store.setStatus('error', 'Failed to start load', err.message)
      store.setLoading(false)
    }
  }

  async function restore(datasetId) {
    stop()
    const gen = generation
    store.setStatus('loading', 'Restoring last session…')

    try {
      const { status, error } = await Api.getStatus(datasetId)
      if (gen !== generation) return

      if (status === 'ready') {
        await _render(datasetId, false, gen)
      } else if (status === 'loading' || status === 'pending') {
        store.setLoading(true)
        store.setStatus('loading', 'Resuming data load…', 'Fetching from Jira…')
        _poll(datasetId, gen)
      } else {
        store.clearData()
        store.setStatus('idle', 'Previous dataset unavailable', 'Click "Load Data" to fetch new data')
      }
    } catch {
      if (gen !== generation) return
      store.setStatus('idle', 'Idle — click "Load Data" to begin')
    }
  }

  function rerender(onCharts) {
    if (store.charts && store.datasetId) {
      onCharts(store.charts, store.datasetId, false)
    }
  }

  function _poll(datasetId, gen) {
    let issueCount = 0
    pollTimer = setInterval(async () => {
      if (gen !== generation) { clearInterval(pollTimer); return }
      try {
        const { status, error, count } = await Api.getStatus(datasetId)
        if (gen !== generation) return

        if (count !== undefined) issueCount = count
        const detail = issueCount > 0 ? `${issueCount} issues fetched so far…` : 'Fetching from Jira…'
        store.setStatus('loading', 'Loading data…', detail)

        if (status === 'ready') {
          clearInterval(pollTimer)
          await _render(datasetId, true, gen)
        } else if (status === 'failed') {
          clearInterval(pollTimer)
          store.setStatus('error', 'Data loading failed', error || 'Unknown error')
          store.setLoading(false)
        }
      } catch (err) {
        if (gen !== generation) return
        clearInterval(pollTimer)
        store.setStatus('error', 'Polling failed', err.message)
        store.setLoading(false)
      }
    }, POLL_MS)
  }

  async function _render(datasetId, saveTimestamp, gen) {
    store.setStatus('loading', 'Rendering charts…')
    try {
      const charts = await Api.getCharts(datasetId)
      if (gen !== generation) return

      store.setCharts(charts, datasetId, saveTimestamp)
      store.setStatus('ready', 'Ready', `Dataset: ${datasetId.substring(0, 8)}…`)
      store.setLoading(false)
    } catch (err) {
      if (gen !== generation) return
      store.setStatus('error', 'Chart rendering failed', err.message)
      store.setLoading(false)
    }
  }

  return { load, restore, stop, rerender }
}
