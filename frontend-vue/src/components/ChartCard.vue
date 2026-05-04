<template>
  <div class="chart-card">
    <div class="chart-card-header">
      <div>
        <div class="chart-card-title">{{ title }}</div>
        <div class="chart-card-desc">{{ description }}</div>
      </div>
      <slot name="controls" />
      <button class="chart-export-btn" @click="exportPng" :aria-label="`Export ${title} as PNG`" title="Export PNG">⬇</button>
    </div>
    <div :id="chartId" class="chart-card-body" ref="chartEl">
      <div class="chart-placeholder">
        <span class="chart-placeholder-icon">{{ icon }}</span>
        <span>Load data to render</span>
      </div>
    </div>
    <div class="chart-callout"></div>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'

const props = defineProps({
  chartId: { type: String, required: true },
  title:   { type: String, required: true },
  description: { type: String, default: '' },
  icon:    { type: String, default: '📊' },
})

const chartEl = ref(null)
const showNotification = inject('showNotification')

function exportPng() {
  const el = chartEl.value
  if (!el || !el._fullLayout) {
    showNotification?.('Load data first to export this chart', 'info')
    return
  }
  window.Plotly.downloadImage(el, { format: 'png', filename: props.chartId, width: 1400, height: 600 })
}

defineExpose({ chartEl })
</script>
