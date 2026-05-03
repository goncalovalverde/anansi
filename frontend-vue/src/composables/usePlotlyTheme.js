const DARK_LAYOUT = {
  paper_bgcolor: '#1a2332',
  plot_bgcolor: '#1e2d40',
  font: { color: '#e8eaf0' },
  xaxis: { gridcolor: 'rgba(255,255,255,0.08)', linecolor: 'rgba(255,255,255,0.15)', zerolinecolor: 'rgba(255,255,255,0.08)' },
  yaxis: { gridcolor: 'rgba(255,255,255,0.08)', linecolor: 'rgba(255,255,255,0.15)', zerolinecolor: 'rgba(255,255,255,0.08)' },
}
const LIGHT_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#2C3E50' },
  xaxis: { gridcolor: 'rgba(0,0,0,0.06)', linecolor: 'rgba(0,0,0,0.1)', zerolinecolor: 'rgba(0,0,0,0.06)' },
  yaxis: { gridcolor: 'rgba(0,0,0,0.06)', linecolor: 'rgba(0,0,0,0.1)', zerolinecolor: 'rgba(0,0,0,0.06)' },
}

export function usePlotlyTheme() {
  function applyTheme(isDark, containerIds) {
    if (!window.Plotly) return
    const layout = isDark ? DARK_LAYOUT : LIGHT_LAYOUT
    for (const id of containerIds) {
      const el = document.getElementById(id)
      if (el && el._fullLayout) {
        window.Plotly.relayout(el, layout)
      }
    }
  }
  return { applyTheme }
}
