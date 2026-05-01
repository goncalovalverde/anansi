<template>
  <div class="kpi-strip" aria-label="Key metrics summary">
    <div class="kpi-box" id="kpi-total">
      <div class="kpi-value">{{ kpis?.total_issues ?? '—' }}</div>
      <div class="kpi-label">Total Issues</div>
    </div>
    <div class="kpi-box kpi-done" id="kpi-done">
      <div class="kpi-value">{{ kpis?.done_count ?? '—' }}</div>
      <div class="kpi-label">Completed</div>
    </div>
    <div class="kpi-box" id="kpi-wip">
      <div class="kpi-value">{{ kpis?.in_progress_count ?? '—' }}</div>
      <div class="kpi-label">In Progress</div>
    </div>
    <div :class="['kpi-box kpi-cycle', trendClass]" id="kpi-cycle">
      <div class="kpi-value">{{ cycleText }}</div>
      <div class="kpi-label">Avg Cycle Time (days)</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDataStore } from '@/stores/data.js'

const store = useDataStore()
const kpis = computed(() => store.kpis)

const trendIcon = { improving: ' ↓', worsening: ' ↑', stable: ' →', neutral: '' }
const cycleText = computed(() => {
  if (!kpis.value) return '—'
  const val = kpis.value.avg_cycle_time_days
  const icon = trendIcon[kpis.value.cycle_trend] || ''
  return val !== undefined ? `${val}d${icon}` : '—'
})
const trendClass = computed(() => {
  const t = kpis.value?.cycle_trend
  return t && t !== 'neutral' ? `kpi-trend-${t}` : ''
})
</script>
