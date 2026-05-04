import { nextTick } from 'vue'

export const ANANSI_COLORS = [
  '#007B85',
  '#F5A623',
  '#D35400',
  '#2C3E50',
  '#5DADE2',
  '#A569BD',
  '#52BE80',
]

export const PLOTLY_CONFIG = {
  displayModeBar: 'hover',
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: [
    'select2d', 'lasso2d', 'autoScale2d',
    'toggleSpikelines', 'hoverClosestCartesian', 'hoverCompareCartesian',
  ],
}

export const EMPTY_PLACEHOLDER_HTML =
  '<div class="chart-placeholder"><span class="chart-placeholder-icon">📊</span><span>No data</span></div>'

export const ERROR_STATE_HTML = `
  <div class="chart-empty-state">
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="8" x2="12" y2="12"/>
      <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
    <span>This chart needs more data - try loading a wider date range or check your workflow configuration.</span>
    <a href="#/config" class="chart-empty-link">Go to Configuration -&gt;</a>
  </div>`

const DEFAULT_CHART_HEIGHT = 260

/**
 * Deep-merges Plotly theme defaults onto a figure's existing layout.
 * Preserves all axis config (type, tickformat, tickangle, etc.) from the
 * backend while layering theme overrides (bgcolor, font, colorway) on top.
 *
 * @param {object} figLayout - The layout from the backend figure.
 * @param {HTMLElement|null} el - The container element. When provided, its
 *   clientHeight is used as layout.height so Plotly never overflows the card.
 *   Falls back to DEFAULT_CHART_HEIGHT (260px) when el is absent or has no
 *   measured height (e.g. hidden tabs, collapsed panels).
 */
export function applyTheme(figLayout, el = null) {
  const base = figLayout || {}
  return {
    ...base,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor:  'rgba(0,0,0,0)',
    font:     { family: 'Inter, Roboto, sans-serif', color: '#2C3E50', size: 12 },
    colorway: ANANSI_COLORS,
    height:   (el?.clientHeight) || DEFAULT_CHART_HEIGHT,
    margin:   { ...(base.margin || {}), t: 16, r: 40, b: 40, l: 50 },
    legend:   { ...(base.legend || {}), orientation: 'h', y: -0.15, xanchor: 'center', x: 0.5 },
    xaxis:    { ...(base.xaxis  || {}), automargin: true },
    yaxis:    { ...(base.yaxis  || {}), automargin: true },
  }
}

/**
 * Returns true when the Python backend returns an error figure
 * (title text contains a known error marker string).
 */
export function isErrorFigure(fig) {
  const titleText = (typeof fig.layout?.title === 'string'
    ? fig.layout.title
    : fig.layout?.title?.text) || ''
  return (
    titleText.includes('unavailable') ||
    titleText.includes('failed') ||
    titleText.includes('No completed') ||
    titleText.includes('needs more data')
  )
}

/**
 * Defers a render callback until after Vue's next DOM flush and one
 * browser animation frame, ensuring Plotly measures real pixel dimensions.
 */
export function deferRender(fn) {
  nextTick(() => requestAnimationFrame(fn))
}
