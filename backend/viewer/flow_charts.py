"""flow_charts.py — chart methods for the Flow view.

This mixin is consumed by ``viewer.backlog.Backlog``. It accesses instance attributes
set up by ``Backlog.__init__`` via normal ``self`` references.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .backlog_data import BacklogData
from .chart_config import ANANSI_COLORS, ChartConfig
from .chart_helpers import _create_empty_state_figure


class FlowChartsMixin:
    """Chart methods rendered on the Flow view."""

    def draw_flow_efficiency(self) -> str:
        df = self.treemap_data
        done_col = self.done_step
        in_prog_col = self.in_progress_step

        if done_col not in df.columns or "Cycle Time" not in df.columns:
            return go.Figure(layout={"title": "flow_efficiency unavailable: No done date column"}).to_json()

        done_mask = df[done_col].notna()
        done_count = int(done_mask.sum())
        if done_count == 0:
            return go.Figure(layout={"title": "flow_efficiency unavailable: No completed items"}).to_json()

        current_wip = 0
        if in_prog_col in df.columns:
            current_wip = int((df[in_prog_col].notna() & ~done_mask).sum())

        total = done_count + current_wip
        efficiency = round(done_count / total * 100, 1) if total > 0 else 0
        color = (
            "#52BE80"
            if efficiency > self.chart_config.FLOW_EFFICIENCY_GOOD_PCT
            else ("#F5A623" if efficiency >= self.chart_config.FLOW_EFFICIENCY_OK_PCT else "#D35400")
        )
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=efficiency,
                number={"suffix": "%", "font": {"size": 28}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": color},
                    "steps": [
                        {"range": [0, 20], "color": "#fdeee5"},
                        {"range": [20, 40], "color": "#fff3dc"},
                        {"range": [40, 100], "color": "#e8f8f0"},
                    ],
                    "threshold": {"line": {"color": "#2C3E50", "width": 2}, "thickness": 0.75, "value": efficiency},
                },
            )
        )
        return fig.to_json()

    def draw_wip_trend(self) -> str:
        df = self.treemap_data
        in_prog_col = self.in_progress_step
        done_col = self.done_step
        done_series = df[done_col] if done_col in df.columns else None

        # Prefer the in-progress entry-date column. Fall back to Created when
        # the step-date column is absent, has no data, or resolves to the same
        # column as done_step (e.g. single-step workflow with no active step column).
        using_fallback = False
        if in_prog_col in df.columns and in_prog_col != done_col and df[in_prog_col].notna().any():
            entry_dates = df[in_prog_col]
        elif "Created" in df.columns:
            entry_dates = df["Created"]
            using_fallback = True
        else:
            return go.Figure(layout={"title": "wip_trend unavailable: No date data"}).to_json()

        wip = BacklogData.build_event_wip(entry_dates, done_series)

        if wip.empty:
            return go.Figure(layout={"title": "wip_trend unavailable: No in-progress data"}).to_json()

        wip_df = pd.DataFrame({"week": wip.index, "wip": wip.values})

        rising = len(wip_df) >= 8 and wip_df["wip"].iloc[-4:].mean() > wip_df["wip"].iloc[-8:-4].mean() * 1.2
        color = ANANSI_COLORS[2] if rising else ANANSI_COLORS[0]
        y_title = "Items in backlog (not done)" if using_fallback else "Items in Progress"

        fig = go.Figure(
            go.Scatter(
                x=wip_df["week"],
                y=wip_df["wip"],
                mode="lines+markers",
                line={"color": color, "width": 2},
                name="WIP",
            )
        )
        fig.update_layout(xaxis={"title": "Week"}, yaxis={"title": y_title})
        return fig.to_json()

    def draw_throughput(self) -> str:
        if self._done_df.empty:
            return go.Figure(layout={"title": "throughput unavailable: No completed items"}).to_json()
        weekly = BacklogData.build_weekly_counts(self._done_df[self.done_step])
        if weekly.empty:
            return go.Figure(layout={"title": "throughput unavailable: No completed items"}).to_json()
        weeks = [str(p.start_time.date()) for p in weekly.index]
        counts = weekly.values.tolist()
        rolling = pd.Series(counts).rolling(4, min_periods=1).mean().round(1).tolist()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=weeks, y=counts, name="Completed", marker_color=ANANSI_COLORS[0]))
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=rolling,
                mode="lines",
                name="4-week avg",
                line={"color": ANANSI_COLORS[1], "width": 2, "dash": "dot"},
            )
        )
        fig.update_layout(xaxis={"type": "category", "tickangle": -30}, yaxis={"title": "Items completed"})
        return fig.to_json()

    def draw_throughput_histogram(self) -> str:
        """Weekly throughput histogram with rolling average and color coding."""
        _EMPTY = "No completed items yet - data will appear once items reach Done status"
        if self._done_df.empty:
            return _create_empty_state_figure(_EMPTY)

        complete_weekly = BacklogData.build_weekly_counts(self._done_df[self.done_step], fill_zeros=True)
        if complete_weekly.empty:
            return _create_empty_state_figure(_EMPTY)

        week_labels = [p.start_time.strftime("%d %b") for p in complete_weekly.index]
        counts = complete_weekly.values.tolist()

        non_zero_counts = [c for c in counts if c > 0]
        if non_zero_counts:
            mean = np.mean(non_zero_counts)
            stddev = np.std(non_zero_counts)
        else:
            mean = 0
            stddev = 0

        colors = []
        for count in counts:
            if count == 0:
                colors.append(ChartConfig.ZERO_WEEK_COLOR)
            elif stddev > 0:
                if count > mean + stddev:
                    colors.append(ChartConfig.ABOVE_MEAN_COLOR)
                elif count < mean - stddev:
                    colors.append(ChartConfig.BELOW_MEAN_COLOR)
                else:
                    colors.append(ChartConfig.NORMAL_WEEK_COLOR)
            else:
                colors.append(ChartConfig.NORMAL_WEEK_COLOR)

        rolling = (
            pd.Series(counts).rolling(self.chart_config.ROLLING_AVG_WINDOW, min_periods=1).mean().round(1).tolist()
        )

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=week_labels,
                y=counts,
                marker=dict(color=colors),
                name="Items completed",
                hovertemplate="%{x}<br>Items: %{y}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=week_labels,
                y=rolling,
                mode="lines",
                name="4-week avg",
                line=dict(color=ChartConfig.ABOVE_MEAN_COLOR, width=2, dash="dot"),
                hovertemplate="%{x}<br>4-week avg: %{y}<extra></extra>",
            )
        )
        fig.update_layout(
            xaxis=dict(tickangle=-45, nticks=12, title=dict(text="")),
            yaxis=dict(title=dict(text="Items / week"), dtick=1),
            bargap=0.2,
            showlegend=True,
            hovermode="x unified",
        )
        return fig.to_json()
