const BASE = ''

async function apiFetch(url, opts = {}) {
  const r = await fetch(BASE + url, opts)
  const data = await r.json()
  if (!r.ok) throw new Error(data?.detail || `HTTP ${r.status}`)
  return data
}

const json = (body) => ({ headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const Api = {
  getConfig:     ()  => apiFetch('/api/config'),
  putConfig:     (d) => apiFetch('/api/config', { method: 'PUT',  ...json(d) }),

  getWorkflow:   ()  => apiFetch('/api/config/workflow'),
  putWorkflow:   (steps) => apiFetch('/api/config/workflow', { method: 'PUT', ...json({ steps }) }),

  getIssueTypes: ()  => apiFetch('/api/config/issue-types'),
  putIssueTypes: (types) => apiFetch('/api/config/issue-types', { method: 'PUT', ...json({ types }) }),

  testConnection:  (d) => apiFetch('/api/config/test-connection',  { method: 'POST', ...json(d || {}) }),
  getJiraStatuses: (d) => apiFetch('/api/config/jira-statuses',    { method: 'POST', ...json(d || {}) }),
  getJiraProjects: (d) => apiFetch('/api/config/jira-projects',    { method: 'POST', ...json(d || {}) }),
  getJiraFields:   (d) => apiFetch('/api/config/jira-fields',      { method: 'POST', ...json(d || {}) }),
  getJiraIssueTypes: (d) => apiFetch('/api/config/jira-issue-types', { method: 'POST', ...json(d || {}) }),

  loadData:     ()   => apiFetch('/api/data/load', { method: 'POST' }),
  uploadCsv:    (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiFetch('/api/data/upload-csv', { method: 'POST', body: fd })
  },
  getStatus:  (id) => apiFetch(`/api/data/${id}/status`),
  getCharts:  (id) => apiFetch(`/api/charts/${id}`),
  getInsights: (id) => apiFetch(`/api/insights/${id}`),
  getFlow:    (id) => apiFetch(`/api/flow/${id}`),
  getTrends:  (id) => apiFetch(`/api/trends/${id}`),
  clearCache: ()   => apiFetch('/api/data/cache', { method: 'DELETE' }),
}
