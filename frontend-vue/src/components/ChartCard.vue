<template>
  <div class="chart-card">
    <div class="chart-card-header">
      <div>
        <div class="chart-card-title">{{ title }}</div>
        <div class="chart-card-desc">{{ description }}</div>
      </div>
      <slot name="controls" />
      <div class="chart-actions">
        <slot name="actions" />
        <button class="chart-action-btn" @click="toggleMaximize" :aria-label="`Maximize ${title}`" title="Maximize">⛶</button>
        <button class="chart-export-btn" @click="exportPng" :aria-label="`Export ${title} as PNG`" title="Export PNG">⬇</button>
      </div>
    </div>
    <div :id="chartId" class="chart-card-body" ref="chartEl">
      <div class="chart-placeholder">
        <span class="chart-placeholder-icon">{{ icon }}</span>
        <span>Load data to render</span>
      </div>
    </div>
    <div class="chart-callout"></div>
  </div>
  
  <!-- Maximize modal -->
  <div v-if="isMaximized" class="chart-modal-overlay" @click="toggleMaximize">
    <div class="chart-modal" @click.stop>
      <div class="chart-modal-header">
        <div>
          <div class="chart-modal-title">{{ title }}</div>
          <div class="chart-modal-desc">{{ description }}</div>
        </div>
        <div class="chart-modal-actions">
          <button class="chart-action-btn" @click="exportPng" title="Export PNG">⬇</button>
          <button class="chart-action-btn" @click="toggleMaximize" title="Close">✕</button>
        </div>
      </div>
      <div :id="`${chartId}-modal`" class="chart-modal-body" ref="modalChartEl"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, inject, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  chartId: { type: String, required: true },
  title:   { type: String, required: true },
  description: { type: String, default: '' },
  icon:    { type: String, default: '📊' },
})

const chartEl = ref(null)
const modalChartEl = ref(null)
const isMaximized = ref(false)
const showNotification = inject('showNotification')

function toggleMaximize() {
  isMaximized.value = !isMaximized.value
  if (isMaximized.value) {
    // Copy chart to modal when maximizing
    setTimeout(() => {
      if (chartEl.value?._fullLayout && modalChartEl.value) {
        window.Plotly.newPlot(modalChartEl.value, chartEl.value.data, chartEl.value.layout)
        // Trigger resize to fill full modal dimensions
        setTimeout(() => {
          window.Plotly.Plots.resize(modalChartEl.value)
        }, 50)
      }
    }, 50)
  }
}

function handleWindowResize() {
  if (isMaximized.value && modalChartEl.value?._fullLayout) {
    window.Plotly.Plots.resize(modalChartEl.value)
  }
}

function exportPng() {
  const el = chartEl.value
  if (!el || !el._fullLayout) {
    showNotification?.('Load data first to export this chart', 'info')
    return
  }
  window.Plotly.downloadImage(el, { format: 'png', filename: props.chartId, width: 1400, height: 600 })
}

// When chart updates, also update the modal if visible
watch(() => chartEl.value?._fullLayout, () => {
  if (isMaximized.value && chartEl.value?._fullLayout && modalChartEl.value) {
    window.Plotly.newPlot(modalChartEl.value, chartEl.value.data, chartEl.value.layout)
  }
})

onMounted(() => {
  window.addEventListener('resize', handleWindowResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
})

defineExpose({ chartEl })
</script>
