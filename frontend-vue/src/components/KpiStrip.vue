<template>
  <div class="kpi-strip" aria-label="Key metrics summary">
    <div class="kpi-box" id="kpi-total">
      <div class="kpi-value" style="color: var(--color-neutral)">{{ kpis?.total_issues ?? '—' }}</div>
      <div class="kpi-label">Total Issues</div>
    </div>
    <div class="kpi-box kpi-done" id="kpi-done" style="border-top: 3px solid var(--color-accent)">
      <div class="kpi-value" :style="{ color: kpis?.done_count === 0 ? 'var(--color-accent)' : 'var(--color-neutral)' }">{{ kpis?.done_count ?? '—' }}</div>
      <div class="kpi-label">Completed</div>
      <div class="kpi-hint" v-if="kpis?.done_count === 0">No items marked Done in this period</div>
    </div>
    <div class="kpi-box" id="kpi-wip" :style="{ borderTop: `3px solid ${(kpis?.in_progress_count ?? 0) > 100 ? 'var(--color-alert)' : 'var(--color-primary)'}` }">
      <div class="kpi-value" :style="{ color: (kpis?.in_progress_count ?? 0) > 100 ? 'var(--color-alert)' : 'var(--color-neutral)' }">{{ kpis?.in_progress_count ?? '—' }}</div>
      <div class="kpi-label">In Progress</div>
      <div class="kpi-hint" v-if="(kpis?.in_progress_count ?? 0) > 100">High WIP - consider limiting work in progress</div>
    </div>
    <div :class="['kpi-box kpi-cycle', trendClass]" id="kpi-cycle" style="border-top: 3px solid var(--color-primary)">
      <div class="kpi-value" style="color: var(--color-neutral)">{{ cycleText }}</div>
      <div class="kpi-label">Avg Cycle Time (days)</div>
      <div class="kpi-hint" v-if="!kpis?.avg_cycle_time_days">Needs completed items to calculate</div>
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
