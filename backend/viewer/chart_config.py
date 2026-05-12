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

# Tunable threshold defaults — can be overridden per-instance via DB config
_THRESHOLD_DEFAULTS = {
    "wip_high_threshold": 100,
    "wip_elevated_threshold": 50,
    "cycle_time_high_days": 30,
    "cycle_time_healthy_days": 10,
    "bug_ratio_high_pct": 30,
    "bug_ratio_elevated_pct": 15,
    "backlog_growth_ratio": 1.2,
    "aging_critical_days": 60,
    "aging_critical_count": 5,
    "aging_warning_days": 31,
    "aging_warning_count": 3,
    "callout_bug_ratio_high_pct": 25,
    "callout_cycle_time_alert_days": 60,
    "callout_cycle_time_warn_days": 30,
    "callout_outlier_ct_multiplier": 3,
    "callout_epic_concentration_pct": 0.6,
    "complexity_ratio_threshold": 3.0,
    "unestimated_items_threshold": 0.2,
    "flow_efficiency_good_pct": 40,
    "flow_efficiency_ok_pct": 20,
    "stddev_threshold": 1.0,
    "rolling_avg_window": 4,
}


class ChartConfig:
    """Centralized configuration for chart generation.

    Style/layout constants remain class-level (never overridden).
    Tunable thresholds are instance attributes, initialized from defaults
    and optionally overridden via a dict (loaded from the config DB).
    """

    # ---- Style / layout constants (class-level, not overridable) ---- #
    HEATMAP_MIN_HEIGHT = 240
    HEATMAP_EPIC_ROW_HEIGHT = 36
    HEATMAP_PADDING = 80
    HEATMAP_COLORSCALE = [
        [0, '#e0f4f5'], [0.25, '#9fd4dc'], [0.5, '#F5A623'],
        [0.75, '#D35400'], [1.0, '#7B1A00']
    ]

    NORMAL_WEEK_COLOR = '#007B85'
    ABOVE_MEAN_COLOR = '#F5A623'
    BELOW_MEAN_COLOR = '#2C3E50'
    ZERO_WEEK_COLOR = '#2C3E50'

    EMPTY_STATE_HEIGHT = 240
    EMPTY_STATE_FONT_SIZE = 13
    EMPTY_STATE_FONT_COLOR = '#888888'

    def __init__(self, overrides: dict | None = None):
        merged = dict(_THRESHOLD_DEFAULTS)
        if overrides:
            for key, value in overrides.items():
                if key in _THRESHOLD_DEFAULTS:
                    merged[key] = type(_THRESHOLD_DEFAULTS[key])(value)

        # Expose thresholds as UPPER_CASE attributes for backward compatibility
        self.WIP_HIGH_THRESHOLD = merged["wip_high_threshold"]
        self.WIP_ELEVATED_THRESHOLD = merged["wip_elevated_threshold"]
        self.CYCLE_TIME_HIGH_DAYS = merged["cycle_time_high_days"]
        self.CYCLE_TIME_HEALTHY_DAYS = merged["cycle_time_healthy_days"]
        self.BUG_RATIO_HIGH_PCT = merged["bug_ratio_high_pct"]
        self.BUG_RATIO_ELEVATED_PCT = merged["bug_ratio_elevated_pct"]
        self.BACKLOG_GROWTH_RATIO = merged["backlog_growth_ratio"]
        self.AGING_CRITICAL_DAYS = merged["aging_critical_days"]
        self.AGING_CRITICAL_COUNT = merged["aging_critical_count"]
        self.AGING_WARNING_DAYS = merged["aging_warning_days"]
        self.AGING_WARNING_COUNT = merged["aging_warning_count"]
        self.CALLOUT_BUG_RATIO_HIGH_PCT = merged["callout_bug_ratio_high_pct"]
        self.CALLOUT_CYCLE_TIME_ALERT_DAYS = merged["callout_cycle_time_alert_days"]
        self.CALLOUT_CYCLE_TIME_WARN_DAYS = merged["callout_cycle_time_warn_days"]
        self.CALLOUT_OUTLIER_CT_MULTIPLIER = merged["callout_outlier_ct_multiplier"]
        self.CALLOUT_EPIC_CONCENTRATION_PCT = merged["callout_epic_concentration_pct"]
        self.COMPLEXITY_RATIO_THRESHOLD = merged["complexity_ratio_threshold"]
        self.UNESTIMATED_ITEMS_THRESHOLD = merged["unestimated_items_threshold"]
        self.FLOW_EFFICIENCY_GOOD_PCT = merged["flow_efficiency_good_pct"]
        self.FLOW_EFFICIENCY_OK_PCT = merged["flow_efficiency_ok_pct"]
        self.STDDEV_THRESHOLD = merged["stddev_threshold"]
        self.ROLLING_AVG_WINDOW = merged["rolling_avg_window"]


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
