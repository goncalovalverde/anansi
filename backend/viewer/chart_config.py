"""chart_config.py — shared constants and color management for the Backlog viewer.

Responsibilities:
  - ANANSI_COLORS palette used by all charts.
  - ChartConfig: numeric thresholds and style constants (no Plotly dependency).
  - EpicColorMap: thread-safe singleton that maps epic names to consistent colors.

Nothing in this module imports Plotly, pandas, or any HTTP framework.
"""

import threading
from typing import Dict, List

ANANSI_COLORS = ['#007B85', '#F5A623', '#D35400', '#2C3E50', '#5DADE2', '#A569BD', '#52BE80']


class ChartConfig:
    """Centralized configuration for chart generation."""
    # Aging Heatmap
    HEATMAP_MIN_HEIGHT = 240
    HEATMAP_EPIC_ROW_HEIGHT = 36
    HEATMAP_PADDING = 80
    HEATMAP_COLORSCALE = [
        [0, '#e0f4f5'], [0.25, '#9fd4dc'], [0.5, '#F5A623'],
        [0.75, '#D35400'], [1.0, '#7B1A00']
    ]

    # Throughput Histogram
    NORMAL_WEEK_COLOR = '#007B85'  # Teal
    ABOVE_MEAN_COLOR = '#F5A623'   # Gold
    BELOW_MEAN_COLOR = '#2C3E50'   # Dark
    ZERO_WEEK_COLOR = '#2C3E50'    # Dark
    STDDEV_THRESHOLD = 1.0
    ROLLING_AVG_WINDOW = 4

    # Callout thresholds
    AGING_CRITICAL_DAYS = 60
    AGING_CRITICAL_COUNT = 5
    AGING_WARNING_DAYS = 31
    AGING_WARNING_COUNT = 3

    COMPLEXITY_RATIO_THRESHOLD = 3.0
    UNESTIMATED_ITEMS_THRESHOLD = 0.2  # 20%

    # Insights thresholds
    WIP_HIGH_THRESHOLD = 100
    WIP_ELEVATED_THRESHOLD = 50
    CYCLE_TIME_HIGH_DAYS = 30
    CYCLE_TIME_HEALTHY_DAYS = 10
    BUG_RATIO_HIGH_PCT = 30
    BUG_RATIO_ELEVATED_PCT = 15
    BACKLOG_GROWTH_RATIO = 1.2

    # Callout thresholds
    CALLOUT_BUG_RATIO_HIGH_PCT = 25
    CALLOUT_CYCLE_TIME_ALERT_DAYS = 60
    CALLOUT_CYCLE_TIME_WARN_DAYS = 30
    CALLOUT_OUTLIER_CT_MULTIPLIER = 3
    CALLOUT_EPIC_CONCENTRATION_PCT = 0.6  # one epic consuming >60% of capacity

    # Flow efficiency gauge colour thresholds
    FLOW_EFFICIENCY_GOOD_PCT = 40
    FLOW_EFFICIENCY_OK_PCT = 20

    # Empty state
    EMPTY_STATE_HEIGHT = 240
    EMPTY_STATE_FONT_SIZE = 13
    EMPTY_STATE_FONT_COLOR = '#888888'


class EpicColorMap:
    """Singleton managing consistent epic-to-color mapping across charts."""
    _instance = None
    _color_map: Dict[str, str] = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def assign_colors(self, epic_names: List[str]) -> Dict[str, str]:
        """Get consistent colors for epic names, assigning new ones as needed."""
        sorted_epics = sorted(set(epic_names))
        with self._lock:
            for i, epic in enumerate(sorted_epics):
                if epic not in self._color_map:
                    self._color_map[epic] = ANANSI_COLORS[i % len(ANANSI_COLORS)]
            return {epic: self._color_map[epic] for epic in epic_names}

    def get_color(self, epic_name: str) -> str:
        """Get color for a single epic, assigning if needed."""
        with self._lock:
            if epic_name not in self._color_map:
                idx = len(self._color_map)
                self._color_map[epic_name] = ANANSI_COLORS[idx % len(ANANSI_COLORS)]
            return self._color_map[epic_name]

    def clear(self):
        """Reset color map (useful for testing)."""
        with self._lock:
            self._color_map.clear()
