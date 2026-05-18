<template>
  <main>
    <div class="container">
      <div class="page-content">

        <!-- Progress strip -->
        <div class="setup-progress">
          <div :class="['progress-step', stepConnect ? 'done' : '']">
            <span class="progress-step-num">{{ stepConnect ? '✓' : '1' }}</span>
            <span class="progress-step-label">Connect</span>
          </div>
          <div class="progress-connector"></div>
          <div :class="['progress-step', stepWorkflow ? 'done' : '']">
            <span class="progress-step-num">{{ stepWorkflow ? '✓' : '2' }}</span>
            <span class="progress-step-label">Workflow</span>
          </div>
          <div class="progress-connector"></div>
          <div :class="['progress-step', stepSave ? 'done' : '']">
            <span class="progress-step-num">{{ stepSave ? '✓' : '3' }}</span>
            <span class="progress-step-label">Save &amp; Go</span>
          </div>
        </div>

        <!-- Section 1: Connection -->
        <section class="config-section">
          <h2 class="section-title">Connect Your Data Source</h2>

          <div class="form-section">
            <div class="form-section-title">Where is your data?</div>
            <div class="radio-group">
              <label class="radio-option">
                <input type="radio" v-model="inputMode" value="jira" /> Jira
              </label>
              <label class="radio-option">
                <input type="radio" v-model="inputMode" value="csv" /> CSV File
              </label>
            </div>
          </div>

          <!-- Jira section -->
          <div v-show="inputMode === 'jira'">

            <div class="form-section">
              <div class="form-section-title">Your Jira Site</div>

              <div class="form-group">
                <label for="jira_url">Jira Site URL</label>
                <input type="url" id="jira_url" v-model="form.jira_url"
                  placeholder="https://yourcompany.atlassian.net" />
                <p class="form-hint">The URL you use to open Jira in your browser.</p>
              </div>

              <div class="form-section-title" style="margin-top:1.5rem;">Log In to Jira</div>

              <div class="form-group">
                <label for="jira_auth_method">Login Method</label>
                <select id="jira_auth_method" v-model="form.jira_auth_method">
                  <option value="pat">Personal Access Token — PAT (Recommended)</option>
                  <option value="basic">Username &amp; Password / API Token</option>
                  <option value="oauth">OAuth 1.0a (Advanced)</option>
                </select>
              </div>

              <!-- PAT -->
              <div v-if="form.jira_auth_method === 'pat'" class="form-group">
                <label for="jira_pat_token">Personal Access Token</label>
                <input type="password" id="jira_pat_token" v-model="form.jira_pat_token"
                  placeholder="Leave blank to keep current" />
                <p class="form-hint">
                  In Jira: click your avatar → <strong>Profile → Personal Access Tokens → Create token</strong>.
                  <a href="https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html"
                    target="_blank" rel="noopener noreferrer">Step-by-step guide ↗</a>
                </p>
              </div>

              <!-- Basic -->
              <div v-if="form.jira_auth_method === 'basic'" class="form-row">
                <div class="form-group">
                  <label for="jira_username">Username (email)</label>
                  <input type="text" id="jira_username" v-model="form.jira_username"
                    placeholder="you@yourcompany.com" autocomplete="username" />
                </div>
                <div class="form-group">
                  <label for="jira_password">Password or API Token</label>
                  <input type="password" id="jira_password" v-model="form.jira_password"
                    placeholder="Leave blank to keep current" autocomplete="current-password" />
                  <p class="form-hint">For Jira Cloud, use an <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noopener noreferrer">API Token ↗</a>.</p>
                </div>
              </div>

              <!-- OAuth -->
              <div v-if="form.jira_auth_method === 'oauth'">
                <div class="form-row">
                  <div class="form-group">
                    <label for="jira_oauth_consumer_key">Consumer Key</label>
                    <input type="text" id="jira_oauth_consumer_key" v-model="form.jira_oauth_consumer_key" placeholder="myconsumerkey" />
                  </div>
                  <div class="form-group">
                    <label for="jira_oauth_key_cert_file">Key Certificate File Path</label>
                    <input type="text" id="jira_oauth_key_cert_file" v-model="form.jira_oauth_key_cert_file" placeholder="/path/to/key.pem" />
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label for="jira_oauth_token">Access Token</label>
                    <input type="password" id="jira_oauth_token" v-model="form.jira_oauth_token" placeholder="Leave blank to keep current" />
                  </div>
                  <div class="form-group">
                    <label for="jira_oauth_token_secret">Token Secret</label>
                    <input type="password" id="jira_oauth_token_secret" v-model="form.jira_oauth_token_secret" placeholder="Leave blank to keep current" />
                  </div>
                </div>
              </div>

              <!-- Test connection -->
              <div class="connection-test-row">
                <button class="btn btn-secondary" @click="testConnection" :disabled="testing">
                  {{ testing ? 'Testing…' : '⚡ Test Connection' }}
                </button>
                <div v-if="testResultText" :class="['test-result', testResultClass]">
                  {{ testResultText }}
                </div>
              </div>

              <details class="advanced-settings">
                <summary>Advanced Settings</summary>
                <div class="advanced-content">
                  <div class="form-group form-group--narrow">
                    <label for="jira_api_version">Jira REST API Version</label>
                    <select id="jira_api_version" v-model="form.jira_api_version">
                      <option value="2">v2 — Jira Server / Data Center</option>
                      <option value="3">v3 — Jira Cloud</option>
                    </select>
                    <p class="form-hint">Use v2 for on-premise Jira. Use v3 for Atlassian Cloud.</p>
                  </div>
                </div>
              </details>
            </div>

            <!-- Project, fields & advanced (revealed after successful connection test) -->
            <div v-if="stepConnect" id="project-fields-section" class="form-section">
              <div class="form-section-title">Project &amp; Fields</div>

              <!-- Project picker -->
              <div v-if="projects.length > 0" class="form-group">
                <label for="jira_project_picker">Select Project</label>
                <div class="field-with-action">
                  <select id="jira_project_picker" v-model="selectedProject" @change="onProjectChange">
                    <option value="">— Choose a project —</option>
                    <option v-for="p in projects" :key="p.key" :value="p.key">{{ p.name }} ({{ p.key }})</option>
                  </select>
                </div>
                <p class="form-hint">Select a project and we'll build the issue filter automatically.</p>
              </div>

              <!-- Story points + epic link -->
              <div class="form-row">
                <div class="form-group">
                  <label for="jira_story_points_field">Story Points Field ID</label>
                  <div class="field-with-action">
                    <input type="text" id="jira_story_points_field" v-model="form.jira_story_points_field"
                      placeholder="customfield_10016" />
                    <button type="button" class="btn btn-secondary btn-sm" @click="detectFields" :disabled="detectingFields">
                      {{ detectingFields ? 'Detecting…' : 'Auto-detect' }}
                    </button>
                  </div>
                  <p class="form-hint" id="fields-hint">{{ fieldsHint }}</p>
                </div>
                <div class="form-group">
                  <label for="jira_epic_link_field">Epic Link Field ID</label>
                  <div class="field-with-action">
                    <input type="text" id="jira_epic_link_field" v-model="form.jira_epic_link_field"
                      placeholder="customfield_10014" />
                    <button type="button" class="btn btn-secondary btn-sm" @click="detectFields" :disabled="detectingFields">
                      {{ detectingFields ? 'Detecting…' : 'Auto-detect' }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- JQL advanced -->
              <details class="advanced-settings" ref="jqlDetails">
                <summary>Advanced: Custom Issue Filter (JQL)</summary>
                <div class="advanced-content">
                  <div class="form-group">
                    <label for="jira_jql_query">Issue Filter (JQL)</label>
                    <input type="text" id="jira_jql_query" v-model="form.jira_jql_query"
                      placeholder="project = MYPROJECT AND issuetype in (Story, Bug, Task) ORDER BY created DESC" />
                    <p class="form-hint">Set automatically when you select a project above.</p>
                  </div>
                </div>
              </details>
            </div>

          </div><!-- /jira section -->

          <!-- CSV section -->
          <div v-show="inputMode === 'csv'" class="form-section">
            <div class="form-section-title">Upload your CSV</div>
            <div class="form-group">
              <div class="file-upload-area"
                :class="{ 'file-upload-dragging': csvDragging, 'file-upload-done': csvFile }"
                @dragover.prevent="csvDragging = true"
                @dragleave.prevent="csvDragging = false"
                @drop.prevent="onCsvDrop"
                @click="$refs.csvFileInput.click()">
                <input ref="csvFileInput" type="file" accept=".csv" class="file-upload-hidden" @change="onCsvFileChange" />
                <template v-if="!csvFile">
                  <span class="file-upload-icon">📂</span>
                  <span class="file-upload-label">Click or drag &amp; drop a CSV file here</span>
                </template>
                <template v-else>
                  <span class="file-upload-icon">{{ csvUploading ? '⏳' : '✅' }}</span>
                  <span class="file-upload-label">{{ csvFile.name }}</span>
                  <span class="file-upload-size">{{ (csvFile.size / 1024).toFixed(1) }} KB</span>
                </template>
              </div>
              <p v-if="csvUploadError" class="form-error">{{ csvUploadError }}</p>
              <p v-else-if="csvUploading" class="form-hint">Uploading and processing…</p>
              <p v-else-if="csvDatasetId" class="form-hint form-hint-success">✓ Ready — click "Save Configuration" then go to the Dashboard.</p>
              <p v-else class="form-hint">The file is processed in memory — nothing is saved to disk.</p>
            </div>
          </div>

        </section>

        <!-- Section 2: Workflow (revealed after connection test) -->
        <section v-if="workflowVisible" class="config-section" id="workflow-section">
          <h2 class="section-title">Workflow &amp; Issue Types</h2>

          <div class="form-section">
            <div class="form-section-title">Workflow Steps</div>
            <div class="workflow-explainer">
              <span class="workflow-explainer-icon">ℹ️</span>
              <span>Arrange your board columns left-to-right — earliest stage to final stage. This order is used to calculate cycle time.</span>
            </div>

            <div class="preset-btns">
              <span style="font-size:0.78rem;color:var(--text-muted);align-self:center;">Quick presets:</span>
              <button type="button" class="btn-preset" @click="applyPreset('scrum')">Scrum</button>
              <button type="button" class="btn-preset" @click="applyPreset('kanban')">Kanban</button>
            </div>

            <div class="workflow-builder">
              <div class="workflow-available">
                <div class="workflow-panel-title">Available Statuses (click to add →)</div>
                <div class="status-chips">
                  <button v-for="s in availableStatuses" :key="s" type="button"
                    class="status-chip" @click="addToWorkflow(s)">{{ s }}</button>
                </div>
              </div>
              <div class="workflow-arrow">→</div>
              <div class="workflow-selected">
                <div class="workflow-panel-title">Your Workflow Order</div>
                <ul class="workflow-list">
                  <li v-for="(step, idx) in workflowSteps" :key="step" class="workflow-item" :data-step="step">
                    <span class="workflow-item-name">{{ step }}</span>
                    <div class="workflow-item-actions">
                      <button class="item-btn" @click="moveStep(idx, -1)" title="Move up">▲</button>
                      <button class="item-btn" @click="moveStep(idx, 1)" title="Move down">▼</button>
                      <button class="item-btn del" @click="removeStep(idx)" title="Remove">✕</button>
                    </div>
                  </li>
                </ul>
                <div class="add-item-row">
                  <input type="text" v-model="workflowInput" placeholder="Add step manually…"
                    @keydown.enter="addWorkflowManual" />
                  <button class="btn btn-secondary btn-sm" @click="addWorkflowManual">+ Add</button>
                </div>
              </div>
            </div>

            <div class="form-row" style="margin-top:1rem;" v-if="workflowSteps.length > 1">
              <div class="form-group">
                <label for="workflow_start_step">Cycle Time Start Step</label>
                <select id="workflow_start_step" v-model="startStep">
                  <option v-for="step in workflowSteps.slice(0, -1)" :key="step" :value="step">{{ step }}</option>
                </select>
                <p class="form-hint">The step that marks when active work begins. Cycle time is measured from this step to the final step.</p>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="form-section-title">Issue Types to Track</div>
            <p class="form-hint">"Total" is always included. Add the types relevant to your team.</p>

            <template v-if="availableIssueTypes.length > 0">
              <div class="workflow-panel-title" style="margin-bottom:0.4rem;">Available (click to add →)</div>
              <div class="status-chips" style="margin-bottom:1rem;">
                <button v-for="t in availableIssueTypes" :key="t" type="button"
                  class="status-chip" @click="addIssueType(t)">{{ t }}</button>
              </div>
            </template>

            <div class="tag-list">
              <span v-for="t in issueTypes" :key="t" class="tag">
                {{ t }}
                <button class="remove-tag" @click="removeType(t)" :title="`Remove ${t}`" :aria-label="`Remove ${t}`">✕</button>
              </span>
            </div>
            <div class="add-item-row">
              <input type="text" v-model="typeInput" placeholder="e.g. Story, Bug, Task…"
                @keydown.enter="addType" />
              <button class="btn btn-secondary btn-sm" @click="addType">+ Add</button>
            </div>
          </div>
        </section>

        <!-- Section 3: Chart Thresholds -->
        <section v-if="workflowVisible" class="config-section">
          <div class="section-header">
            <h2 class="section-title">Chart Thresholds</h2>
            <button class="btn btn-secondary btn-sm" @click="resetThresholds">↺ Reset All to Defaults</button>
          </div>
          <p class="form-hint" style="margin-bottom:1rem;">Fine-tune the sensitivity of insights, callouts, and health indicators. Changes apply on the next data load.</p>

          <details class="advanced-settings">
            <summary>WIP &amp; Flow</summary>
            <div class="advanced-content threshold-grid">
              <div class="form-group form-group--narrow">
                <label for="ct_wip_high">WIP High Threshold</label>
                <input type="number" id="ct_wip_high" v-model.number="thresholds.wip_high_threshold" />
                <p class="form-hint">Items count above which WIP is flagged as critical.</p>
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_wip_elevated">WIP Elevated Threshold</label>
                <input type="number" id="ct_wip_elevated" v-model.number="thresholds.wip_elevated_threshold" />
                <p class="form-hint">Items count for elevated WIP warning.</p>
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_flow_good">Flow Efficiency Good (%)</label>
                <input type="number" id="ct_flow_good" v-model.number="thresholds.flow_efficiency_good_pct" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_flow_ok">Flow Efficiency OK (%)</label>
                <input type="number" id="ct_flow_ok" v-model.number="thresholds.flow_efficiency_ok_pct" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_rolling_avg">Rolling Avg Window (weeks)</label>
                <input type="number" id="ct_rolling_avg" v-model.number="thresholds.rolling_avg_window" />
              </div>
            </div>
          </details>

          <details class="advanced-settings">
            <summary>Cycle Time</summary>
            <div class="advanced-content threshold-grid">
              <div class="form-group form-group--narrow">
                <label for="ct_ct_high">High Cycle Time (days)</label>
                <input type="number" id="ct_ct_high" v-model.number="thresholds.cycle_time_high_days" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_ct_healthy">Healthy Cycle Time (days)</label>
                <input type="number" id="ct_ct_healthy" v-model.number="thresholds.cycle_time_healthy_days" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_stddev">Std Dev Threshold</label>
                <input type="number" step="0.1" id="ct_stddev" v-model.number="thresholds.stddev_threshold" />
              </div>
            </div>
          </details>

          <details class="advanced-settings">
            <summary>Bug Ratio &amp; Health</summary>
            <div class="advanced-content threshold-grid">
              <div class="form-group form-group--narrow">
                <label for="ct_bug_high">Bug Ratio High (%)</label>
                <input type="number" id="ct_bug_high" v-model.number="thresholds.bug_ratio_high_pct" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_bug_elevated">Bug Ratio Elevated (%)</label>
                <input type="number" id="ct_bug_elevated" v-model.number="thresholds.bug_ratio_elevated_pct" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_backlog_growth">Backlog Growth Ratio</label>
                <input type="number" step="0.1" id="ct_backlog_growth" v-model.number="thresholds.backlog_growth_ratio" />
                <p class="form-hint">Created/Done ratio above which backlog is considered growing.</p>
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_complexity">Complexity Ratio</label>
                <input type="number" step="0.1" id="ct_complexity" v-model.number="thresholds.complexity_ratio_threshold" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_unestimated">Unestimated Items (%)</label>
                <input type="number" step="0.01" id="ct_unestimated" v-model.number="thresholds.unestimated_items_threshold" />
                <p class="form-hint">Fraction (0–1) of unestimated items to flag.</p>
              </div>
            </div>
          </details>

          <details class="advanced-settings">
            <summary>Aging</summary>
            <div class="advanced-content threshold-grid">
              <div class="form-group form-group--narrow">
                <label for="ct_aging_crit_days">Aging Critical (days)</label>
                <input type="number" id="ct_aging_crit_days" v-model.number="thresholds.aging_critical_days" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_aging_crit_count">Aging Critical Count</label>
                <input type="number" id="ct_aging_crit_count" v-model.number="thresholds.aging_critical_count" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_aging_warn_days">Aging Warning (days)</label>
                <input type="number" id="ct_aging_warn_days" v-model.number="thresholds.aging_warning_days" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_aging_warn_count">Aging Warning Count</label>
                <input type="number" id="ct_aging_warn_count" v-model.number="thresholds.aging_warning_count" />
              </div>
            </div>
          </details>

          <details class="advanced-settings">
            <summary>Callout Sensitivity</summary>
            <div class="advanced-content threshold-grid">
              <div class="form-group form-group--narrow">
                <label for="ct_co_bug">Bug Ratio High (%)</label>
                <input type="number" id="ct_co_bug" v-model.number="thresholds.callout_bug_ratio_high_pct" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_co_ct_alert">Cycle Time Alert (days)</label>
                <input type="number" id="ct_co_ct_alert" v-model.number="thresholds.callout_cycle_time_alert_days" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_co_ct_warn">Cycle Time Warning (days)</label>
                <input type="number" id="ct_co_ct_warn" v-model.number="thresholds.callout_cycle_time_warn_days" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_co_outlier">Outlier CT Multiplier</label>
                <input type="number" step="0.1" id="ct_co_outlier" v-model.number="thresholds.callout_outlier_ct_multiplier" />
              </div>
              <div class="form-group form-group--narrow">
                <label for="ct_co_epic">Epic Concentration (%)</label>
                <input type="number" step="0.01" id="ct_co_epic" v-model.number="thresholds.callout_epic_concentration_pct" />
                <p class="form-hint">Fraction (0–1) of work in one epic to flag concentration risk.</p>
              </div>
            </div>
          </details>
        </section>

        <!-- Post-save CTA -->
        <div v-if="stepSave" class="cta-banner">
          <p>✓ Configuration saved! Your dashboard is ready.</p>
          <router-link to="/" class="btn btn-success">Go to Dashboard →</router-link>
        </div>

        <!-- Action bar -->
        <div class="action-bar">
          <button class="btn btn-primary" @click="save" :disabled="saving">
            {{ saving ? 'Saving…' : '💾 Save Configuration' }}
          </button>
          <span class="spacer"></span>
          <button class="btn btn-danger" @click="clearConfigCache">🗑 Clear Cache</button>
        </div>

      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject, nextTick } from 'vue'
import { Api } from '@/api/index.js'

const showNotification = inject('showNotification')

// ── Form state ────────────────────────────────────────────────────────────
const inputMode = ref('jira')
const form = reactive({
  jira_url: '',
  jira_jql_query: '',
  jira_auth_method: 'pat',
  jira_api_version: '2',
  jira_username: '',
  jira_password: '',
  jira_pat_token: '',
  jira_story_points_field: '',
  jira_epic_link_field: '',
  jira_oauth_consumer_key: '',
  jira_oauth_key_cert_file: '',
  jira_oauth_token: '',
  jira_oauth_token_secret: '',
  input_csv_file: '',
})

// ── Progress ──────────────────────────────────────────────────────────────
const stepConnect  = ref(false)
const stepWorkflow = ref(false)
const stepSave     = ref(false)

// ── Connection test ───────────────────────────────────────────────────────
const testing = ref(false)
const testResultText  = ref('')
const testResultClass = ref('')

// ── Project picker ────────────────────────────────────────────────────────
const projects = ref([])
const selectedProject = ref('')
const jqlDetails = ref(null)

// ── Field auto-detect ─────────────────────────────────────────────────────
const detectingFields = ref(false)
const fieldsHint = ref('Connect successfully first, then click Auto-detect to find your custom field IDs.')

// ── Workflow ──────────────────────────────────────────────────────────────
const workflowVisible  = ref(false)
const allStatuses      = ref([])
const workflowSteps    = ref([])
const workflowInput    = ref('')
const startStep        = ref('')
const availableStatuses = computed(() =>
  allStatuses.value.filter(s => !workflowSteps.value.includes(s))
)

const PRESETS = {
  scrum:  ['To Do', 'In Progress', 'In Review', 'Done'],
  kanban: ['Backlog', 'Ready', 'In Progress', 'Review', 'Done'],
}

function applyPreset(name) {
  workflowSteps.value = [...(PRESETS[name] || [])]
  startStep.value = workflowSteps.value[1] || ''
}

function addToWorkflow(s) {
  if (!workflowSteps.value.includes(s)) workflowSteps.value.push(s)
}

function moveStep(idx, dir) {
  const arr = [...workflowSteps.value]
  const target = idx + dir
  if (target < 0 || target >= arr.length) return
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
  workflowSteps.value = arr
}

function removeStep(idx) {
  const removed = workflowSteps.value.splice(idx, 1)[0]
  if (inputMode.value === 'jira' && !allStatuses.value.includes(removed)) {
    allStatuses.value.push(removed)
  }
}

function addWorkflowManual() {
  const v = workflowInput.value.trim()
  if (v && !workflowSteps.value.includes(v)) {
    workflowSteps.value.push(v)
    workflowInput.value = ''
  }
}

// ── Issue types ───────────────────────────────────────────────────────────
const issueTypes    = ref([])
const allIssueTypes = ref([])
const typeInput     = ref('')

// ── Chart thresholds ─────────────────────────────────────────────────────
const thresholds = reactive({})
const thresholdDefaults = ref({})

async function resetThresholds() {
  try {
    const defaults = await Api.resetChartThresholds()
    Object.assign(thresholds, defaults)
    showNotification?.('Thresholds reset to defaults', 'info')
  } catch (err) {
    showNotification?.('Reset failed: ' + err.message, 'error')
  }
}

const availableIssueTypes = computed(() =>
  allIssueTypes.value.filter(t => !issueTypes.value.includes(t))
)

function addIssueType(t) {
  if (!issueTypes.value.includes(t)) issueTypes.value.push(t)
}

function addType() {
  const v = typeInput.value.trim()
  if (v && !issueTypes.value.includes(v)) {
    issueTypes.value.push(v)
    typeInput.value = ''
  }
}

function removeType(t) {
  issueTypes.value = issueTypes.value.filter(x => x !== t)
}

// ── Collect form data for API ─────────────────────────────────────────────
function collectFormData() {
  const data = { input_mode: inputMode.value, workflow_start_step: startStep.value }
  const SECRET_FIELDS = ['jira_password', 'jira_pat_token', 'jira_oauth_token', 'jira_oauth_token_secret']
  for (const [key, val] of Object.entries(form)) {
    if (typeof val === 'string') {
      if (SECRET_FIELDS.includes(key) && (val === '' || val === '***')) continue
      if (val === '') continue
    }
    data[key] = val
  }
  return data
}

// ── Test connection ───────────────────────────────────────────────────────
async function testConnection() {
  testing.value = true
  testResultText.value = ''
  testResultClass.value = ''
  try {
    const result = await Api.testConnection(collectFormData())
    if (!result.success) {
      testResultText.value = `✗ ${result.error || 'Connection failed'}`
      testResultClass.value = 'error'
      return
    }
    testResultText.value = '✓ Connection successful — fetching available statuses…'
    testResultClass.value = 'success'

    try {
      const formData = collectFormData()
      const [{ statuses }, issueTypesResult] = await Promise.all([
        Api.getJiraStatuses(formData),
        Api.getJiraIssueTypes(formData).catch(() => ({ issue_types: [] })),
      ])
      allStatuses.value = statuses || []
      allIssueTypes.value = issueTypesResult.issue_types || []
      testResultText.value = `✓ Connected — ${allStatuses.value.length} workflow statuses available`

      // Load project picker
      try {
        const { projects: ps } = await Api.getJiraProjects(formData)
        if (ps?.length) {
          projects.value = ps
          const match = form.jira_jql_query.match(/project\s*=\s*["']?([A-Z0-9_]+)["']?/i)
          if (match) selectedProject.value = match[1]
        }
      } catch { /* silently skip */ }

      stepConnect.value = true
      workflowVisible.value = true
      await nextTick()
      document.getElementById('project-fields-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } catch {
      workflowVisible.value = true
      testResultText.value = '✓ Connected (could not fetch statuses)'
    }
  } catch (err) {
    testResultText.value = `✗ ${err.message}`
    testResultClass.value = 'error'
  } finally {
    testing.value = false
  }
}

function onProjectChange() {
  if (!selectedProject.value) return
  form.jira_jql_query = `project = ${selectedProject.value} ORDER BY created DESC`
  if (jqlDetails.value) jqlDetails.value.open = true
}

// ── Field auto-detect ─────────────────────────────────────────────────────
async function detectFields() {
  detectingFields.value = true
  try {
    const { story_points, epic_link, all_custom_fields } = await Api.getJiraFields(collectFormData())
    if (story_points?.length) {
      form.jira_story_points_field = story_points[0].id
      showNotification?.(`Story Points field detected: ${story_points[0].name} (${story_points[0].id})`, 'success')
    } else {
      showNotification?.('No story points field found — your team may not use story points.', 'info')
    }
    if (epic_link?.length) {
      form.jira_epic_link_field = epic_link[0].id
      showNotification?.(`Epic Link field detected: ${epic_link[0].name} (${epic_link[0].id})`, 'success')
    } else {
      showNotification?.('No epic link field found — epics may use a different field name.', 'info')
    }
    const detected = [story_points?.length && 'story points', epic_link?.length && 'epic link'].filter(Boolean)
    if (detected.length) {
      fieldsHint.value = `Detected: ${detected.join(' and ')}. Values pre-filled — verify and save.`
    } else if (all_custom_fields?.length) {
      fieldsHint.value = `No fields auto-matched. Available custom fields: ${all_custom_fields.map(f => `${f.name} (${f.id})`).join(', ')}`
    } else {
      fieldsHint.value = 'No matching fields found. Enter IDs manually.'
    }
  } catch (err) {
    showNotification?.('Auto-detect failed: ' + err.message, 'error')
  } finally {
    detectingFields.value = false
  }
}

// ── CSV upload ────────────────────────────────────────────────────────────
const csvFile       = ref(null)
const csvDragging   = ref(false)
const csvUploading  = ref(false)
const csvUploadError = ref('')
const csvDatasetId  = ref('')

async function uploadCsv(file) {
  csvFile.value = file
  csvUploadError.value = ''
  csvDatasetId.value = ''
  csvUploading.value = true
  try {
    const { dataset_id } = await Api.uploadCsv(file)
    csvDatasetId.value = dataset_id
    // Persist dataset id to localStorage so the dashboard can pick it up
    localStorage.setItem('anansi_last_dataset_id', dataset_id)
    localStorage.setItem('anansi_last_loaded_ts', Date.now().toString())
    showNotification?.(`CSV processed — ${file.name}`, 'success')
  } catch (err) {
    csvUploadError.value = err.message
  } finally {
    csvUploading.value = false
  }
}

function onCsvFileChange(e) {
  const file = e.target.files?.[0]
  if (file) uploadCsv(file)
}

function onCsvDrop(e) {
  csvDragging.value = false
  const file = e.dataTransfer.files?.[0]
  if (file) uploadCsv(file)
}


const saving = ref(false)

async function save() {
  saving.value = true
  try {
    await Promise.all([
      Api.putConfig(collectFormData()),
      Api.putWorkflow(workflowSteps.value),
      Api.putIssueTypes(issueTypes.value),
      Api.putChartThresholds(thresholds),
    ])
    showNotification?.('Configuration saved successfully', 'success')
    stepSave.value = true
    if (workflowSteps.value.length > 0) stepWorkflow.value = true
  } catch (err) {
    showNotification?.('Save failed: ' + err.message, 'error')
  } finally {
    saving.value = false
  }
}

// ── Clear cache ───────────────────────────────────────────────────────────
async function clearConfigCache() {
  if (!confirm('Delete all cached datasets?')) return
  try {
    const { deleted } = await Api.clearCache()
    showNotification?.(`Cleared ${deleted} cached dataset(s)`, 'info')
  } catch (err) {
    showNotification?.('Failed to clear cache: ' + err.message, 'error')
  }
}

// ── Load config on mount ──────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [configResp, workflowResp, typesResp, thresholdsResp] = await Promise.all([
      Api.getConfig(),
      Api.getWorkflow(),
      Api.getIssueTypes(),
      Api.getChartThresholds(),
    ])

    // Populate form
    for (const [key, value] of Object.entries(configResp)) {
      if (key === 'input_mode') { inputMode.value = value; continue }
      if (key in form && value !== '***') form[key] = value
    }

    workflowSteps.value = workflowResp.steps || []
    issueTypes.value = typesResp.types || []

    // Populate chart thresholds
    Object.assign(thresholds, thresholdsResp)

    const savedStart = configResp.workflow_start_step
    if (savedStart && workflowSteps.value.includes(savedStart)) {
      startStep.value = savedStart
    } else if (workflowSteps.value.length > 1) {
      startStep.value = workflowSteps.value[1]
    }

    if (workflowSteps.value.length > 0) {
      workflowVisible.value = true
      stepWorkflow.value = true
    }

    // Restore post-connection section for previously configured Jira setups
    if (inputMode.value === 'jira' && form.jira_url) {
      stepConnect.value = true
    }
  } catch (err) {
    showNotification?.('Failed to load configuration: ' + err.message, 'error')
  }
})
</script>
