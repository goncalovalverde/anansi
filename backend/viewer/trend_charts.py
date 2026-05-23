"""trend_charts.py — chart methods for the Trends view.

This mixin is consumed by ``viewer.backlog.Backlog``. It accesses instance attributes
set up by ``Backlog.__init__`` via normal ``self`` references.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .backlog_data import BacklogData
from .chart_config import ANANSI_COLORS
from .chart_helpers import _fig_to_dict


class TrendChartsMixin:
    """Chart methods rendered on the Trends view."""

    def draw_cumulative_flow(self) -> dict:
        df = self.treemap_data
        if "Created" not in df.columns:
            return _fig_to_dict(go.Figure(layout={"title": "cumulative_flow unavailable: No Created date column"}))

        created = pd.to_datetime(df["Created"], errors="coerce").dropna()
        if created.empty:
            return _fig_to_dict(go.Figure(layout={"title": "cumulative_flow unavailable: No date data"}))

        done_dates = (
            pd.to_datetime(self._done_df[self.done_step], errors="coerce").dropna()
            if not self._done_df.empty
            else pd.Series([], dtype="datetime64[ns]")
        )
        date_max = max(created.max(), done_dates.max()) if len(done_dates) > 0 else created.max()
        week_range = pd.date_range(start=created.min(), end=date_max, freq="W")

        cum_created = BacklogData.build_cumulative_series(created, week_range)
        cum_done = BacklogData.build_cumulative_series(done_dates, week_range)

        xs = [str(d.date()) for d in week_range]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=cum_created.tolist(),
                mode="lines",
                name="Created",
                line={"color": ANANSI_COLORS[1], "width": 2},
                fill="tonexty",
                fillcolor="rgba(0,123,133,0.1)",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=cum_done.tolist(),
                mode="lines",
                name="Completed",
                line={"color": ANANSI_COLORS[0], "width": 2},
            )
        )
        fig.update_layout(
            xaxis={"tickformat": "%b %Y", "tickangle": -30},
            yaxis={"title": "Cumulative items"},
        )
        return _fig_to_dict(fig)

    def draw_monthly_throughput(self) -> dict:
        if self._done_df.empty:
            return _fig_to_dict(go.Figure(layout={"title": "monthly_throughput unavailable: No completed items"}))
        done_dates = self._done_df[self.done_step].dropna()
        monthly = done_dates.dt.to_period("M").value_counts().sort_index()
        xs = [str(p) for p in monthly.index]
        ys = monthly.values.tolist()
        x_nums = np.arange(len(ys))
        if len(ys) >= 2:
            m, b = np.polyfit(x_nums, ys, 1)
            trend = [round(m * i + b, 1) for i in x_nums]
        else:
            trend = ys[:]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=xs, y=ys, name="Monthly completions", marker_color=ANANSI_COLORS[0]))
        fig.add_trace(
            go.Scatter(
                x=xs, y=trend, mode="lines", name="Trend", line={"color": ANANSI_COLORS[2], "width": 2, "dash": "dot"}
            )
        )
        fig.update_layout(
            xaxis={"type": "category", "tickangle": -30},
            yaxis={"title": "Items completed"},
        )
        return _fig_to_dict(fig)

    def draw_epic_progress(self) -> dict:
        if self._done_df.empty:
            return _fig_to_dict(go.Figure(layout={"title": "epic_progress unavailable: No completed items"}))
        done_col = self.done_step
        done_data = self._done_df
        epic_groups = done_data.groupby("Epic Name")[done_col]
        epic_first = epic_groups.min().dropna()
        epic_last = epic_groups.max().dropna()
        epic_count = done_data.groupby("Epic Name").size()
        epics = sorted(set(epic_first.index) & set(epic_last.index))
        if not epics:
            return _fig_to_dict(go.Figure(layout={"title": "epic_progress unavailable: No completed items"}))
        epic_df = pd.DataFrame(
            [
                {"Epic": e, "Start": epic_first[e], "End": epic_last[e], "Count": int(epic_count.get(e, 1))}
                for e in epics
            ]
        )
        fig = px.timeline(
            epic_df, x_start="Start", x_end="End", y="Epic", color="Epic", color_discrete_sequence=ANANSI_COLORS
        )
        fig.update_layout(showlegend=False, yaxis={"automargin": True})
        return _fig_to_dict(fig)
