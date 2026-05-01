const BASE = ''

export const Api = {
  getConfig:     ()       => fetch(`${BASE}/api/config`).then(r => r.json()),
  putConfig:     (data)   => fetch(`${BASE}/api/config`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json()),

  getWorkflow:   ()       => fetch(`${BASE}/api/config/workflow`).then(r => r.json()),
  putWorkflow:   (steps)  => fetch(`${BASE}/api/config/workflow`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steps }),
  }).then(r => r.json()),

  getIssueTypes: ()       => fetch(`${BASE}/api/config/issue-types`).then(r => r.json()),
  putIssueTypes: (types)  => fetch(`${BASE}/api/config/issue-types`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ types }),
  }).then(r => r.json()),

  testConnection:  (d) => fetch(`${BASE}/api/config/test-connection`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d || {}),
  }).then(r => r.json()),

  getJiraStatuses: (d) => fetch(`${BASE}/api/config/jira-statuses`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d || {}),
  }).then(r => r.json()),

  getJiraProjects: (d) => fetch(`${BASE}/api/config/jira-projects`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d || {}),
  }).then(r => r.json()),

  getJiraFields: (d) => fetch(`${BASE}/api/config/jira-fields`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d || {}),
  }).then(r => r.json()),

  loadData:  () => fetch(`${BASE}/api/data/load`, { method: 'POST' }).then(r => r.json()),
  getStatus: (id) => fetch(`${BASE}/api/data/${id}/status`).then(r => r.json()),
  getCharts: (id) => fetch(`${BASE}/api/charts/${id}`).then(r => r.json()),
  clearCache: () => fetch(`${BASE}/api/data/cache`, { method: 'DELETE' }).then(r => r.json()),
}
