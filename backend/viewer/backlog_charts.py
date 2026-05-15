"""backlog_charts.py — chart methods for the Dashboard / Backlog Composition view.

This mixin is consumed by ``viewer.backlog.Backlog``. It accesses instance attributes
set up by ``Backlog.__init__`` (``self.treemap_data``, ``self._done_df``, etc.) via
normal ``self`` references; no direct dependency on the ``Backlog`` class itself.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .chart_config import ANANSI_COLORS, ChartConfig, EpicColorMap
from .chart_helpers import _create_empty_state_figure


class BacklogChartsMixin:
    """Chart methods rendered on the Dashboard and Backlog Composition views."""

    def draw_treemap(self) -> str:
        """Treemap of completed work only, coloured by Epic."""
        done_data = self._done_df
        if done_data.empty:
            return go.Figure(layout={"title": f"No completed items — need '{self.done_step}' dates"}).to_json()

        done_data = done_data.assign(Count=1)

        fig = px.treemap(
            done_data,
            path=["Epic Name", "Type", "Composed"],
            values="Count",
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
            hover_name="Composed",
            hover_data={"Count": True, "Epic Name": False, "Type": False, "Composed": False},
        )
        fig.update_traces(
            textinfo="label+value+percent parent",
            hovertemplate="<b>%{label}</b><br>Count: %{customdata[0]}<extra></extra>",
            textfont_size=11,
            marker_line_width=2,
            marker_line_color="#F9F9F7",
        )
        return fig.to_json()

    def draw_treemap_all(self) -> str:
        """Treemap of all work, coloured by normalized status bucket."""
        if self.treemap_data.empty:
            return go.Figure(layout={"title": "No data available"}).to_json()
        df = self.treemap_data.assign(
            Count=1,
            Progress=self.treemap_data["Status"].apply(self._normalize_status),
        )
        color_map = {
            "Done": ANANSI_COLORS[0],
            "In Progress": ANANSI_COLORS[1],
            "To Do": ANANSI_COLORS[3],
        }
        fig = px.treemap(
            df,
            path=["Epic Name", "Type", "Composed"],
            values="Count",
            color="Progress",
            color_discrete_map=color_map,
            hover_name="Composed",
            hover_data={"Count": True, "Epic Name": False, "Type": False, "Composed": False, "Progress": False},
        )
        fig.update_traces(
            textinfo="label+value+percent parent",
            hovertemplate="<b>%{label}</b><br>Count: %{customdata[0]}<extra></extra>",
            textfont_size=11,
            marker_line_width=2,
            marker_line_color="#F9F9F7",
        )
        return fig.to_json()

    def draw_distribution(self) -> str:
        date_cols = [c for c in [self.done_step, self.in_progress_step] if c in self.treemap_data.columns]
        df = self.treemap_data[["Epic Name"] + date_cols].copy()
        long = df.melt(id_vars="Epic Name", value_vars=date_cols, var_name="Stage", value_name="Date")
        long = long.dropna(subset=["Date"])
        color_map = {
            self.done_step: ANANSI_COLORS[0],
            self.in_progress_step: ANANSI_COLORS[1],
        }
        fig = px.scatter(
            long,
            x="Date",
            y="Epic Name",
            color="Stage",
            color_discrete_map=color_map,
            title=f"{self.done_step} and {self.in_progress_step} dates",
        )
        return fig.to_json()

    def draw_issues_histogram(self, date_column: str) -> str:
        df = self.treemap_data.dropna(subset=[date_column])
        if df.empty:
            return go.Figure(layout={"title": f"No data for {date_column}"}).to_json()
        fig = px.histogram(
            df,
            x=date_column,
            title=f"{date_column} PBI's per Epic",
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
        )
        return fig.to_json()

    def draw_story_points(self) -> str:
        sp_col = "Story Points"
        if sp_col not in self.treemap_data.columns:
            return go.Figure(layout={"title": "story_points unavailable: Story Points column missing"}).to_json()
        df = self.treemap_data.copy()
        df[sp_col] = pd.to_numeric(df[sp_col], errors="coerce").fillna(0)
        agg = df.groupby("Epic Name", as_index=False)[sp_col].sum()
        if agg[sp_col].sum() == 0:
            return go.Figure(layout={"title": "story_points unavailable: No story points data"}).to_json()

        agg_dict = agg.to_dict(orient="records")
        fig = go.Figure()
        for i, row in enumerate(agg_dict):
            fig.add_trace(
                go.Bar(
                    x=[row["Epic Name"]],
                    y=[row[sp_col]],
                    name=row["Epic Name"],
                    marker=dict(color=ANANSI_COLORS[i % len(ANANSI_COLORS)]),
                    legendgroup=row["Epic Name"],
                    showlegend=True,
                )
            )
        fig.update_layout(
            xaxis=dict(type="category", tickangle=-30, automargin=True, showticklabels=False),
            barmode="relative",
        )
        return fig.to_json()

    def draw_type_issue(self) -> str:
        fig = px.histogram(
            self.treemap_data,
            x="Type",
            title="Type of issue",
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
        )
        return fig.to_json()

    def draw_timeline_size(self) -> str:
        if self._done_df.empty:
            return go.Figure(layout={"title": f"No data — No issues have {self.done_step} date assigned"}).to_json()

        done_data = self._done_df.copy()
        min_ct = float(done_data["Cycle Time"].min())
        max_ct = float(done_data["Cycle Time"].max())

        def _scale(ct: float) -> float:
            """Map cycle time to a direct pixel diameter in the 5–50 range."""
            if max_ct > min_ct:
                return round(5 + 45 * (ct - min_ct) / (max_ct - min_ct), 1)
            return 15.0

        # Create one trace per epic without a size column so Plotly does not
        # install its own sizeref/sizemode scaling — then inject pixel sizes directly.
        fig = px.scatter(
            done_data,
            x=self.done_step,
            y="Epic Name",
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
            hover_name="Summary",
            title="When things were done and how big",
        )

        hover = (
            "<b>%{hovertext}</b><br>"
            + self.done_step
            + ": %{x|%Y-%m-%d}<br>"
            + "Cycle Time: %{customdata[0]}<br>"
            + "Epic: %{y}<extra></extra>"
        )
        for trace in fig.data:
            epic_mask = done_data["Epic Name"] == trace.name
            epic_ct = done_data.loc[epic_mask, "Cycle Time"]
            trace.customdata = [[f"{int(ct)} days"] for ct in epic_ct]
            trace.hovertemplate = hover
            trace.marker.size = [_scale(ct) for ct in epic_ct]

        return fig.to_json()

    def draw_aging_heatmap(self) -> str:
        """Heatmap of active backlog items by age and epic."""
        active_df = self._active_df

        if active_df.empty:
            return _create_empty_state_figure("No active backlog items - everything has reached Done status")

        if "Created" not in active_df.columns:
            return go.Figure(layout={"title": "aging_heatmap unavailable: No Created date"}).to_json()

        today = pd.Timestamp(datetime.now().date())
        created = pd.to_datetime(active_df["Created"], errors="coerce")
        age_days = (today - created).dt.days.fillna(0)

        def assign_bucket(days: int) -> str:
            if days <= 7:
                return "0-7d"
            if days <= 14:
                return "8-14d"
            if days <= 30:
                return "15-30d"
            if days <= 60:
                return "31-60d"
            return "60d+"

        age_buckets = age_days.apply(assign_bucket)
        grouped = active_df.assign(Age_Bucket=age_buckets)
        count_dict = {
            (epic, bucket): len(group) for (epic, bucket), group in grouped.groupby(["Epic Name", "Age_Bucket"])
        }

        epic_counts = active_df["Epic Name"].value_counts()
        epics = epic_counts.index.tolist()
        age_order = ["0-7d", "8-14d", "15-30d", "31-60d", "60d+"]

        z_data = [[int(count_dict.get((epic, bucket), 0)) for bucket in age_order] for epic in epics]

        height = max(
            ChartConfig.HEATMAP_MIN_HEIGHT,
            len(epics) * ChartConfig.HEATMAP_EPIC_ROW_HEIGHT + ChartConfig.HEATMAP_PADDING,
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=z_data,
                x=age_order,
                y=epics,
                colorscale=ChartConfig.HEATMAP_COLORSCALE,
                text=[[str(v) if v > 0 else "" for v in row] for row in z_data],
                texttemplate="%{text}",
                hovertemplate="%{y} / %{x}: %{z} items<extra></extra>",
                showscale=True,
                colorbar=dict(title=dict(text="Items"), thickness=12, len=0.8),
            )
        )
        fig.update_layout(
            xaxis=dict(side="top", tickfont=dict(size=12)),
            yaxis=dict(tickfont=dict(size=11), automargin=True),
            margin=dict(t=48, r=80, b=16, l=120),
            height=height,
            showlegend=False,
        )
        return fig.to_json()

    def draw_epic_investment(self) -> str:
        """Side-by-side treemaps: epic scope by item count vs story points."""
        df = self.treemap_data

        epic_groups = (
            df.groupby("Epic Name")
            .agg(
                {
                    "Key": "count",
                    "Story Points": lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum(),
                }
            )
            .reset_index()
        )
        epic_groups.columns = ["Epic", "ItemCount", "StoryPoints"]
        epic_groups = epic_groups[epic_groups["ItemCount"] > 0].sort_values("ItemCount", ascending=False)

        if epic_groups.empty:
            return _create_empty_state_figure("epic_investment unavailable: No epic data")

        color_map = EpicColorMap()
        epic_colors = [color_map.get_color(epic) for epic in epic_groups["Epic"]]
        has_story_points = epic_groups["StoryPoints"].sum() > 0

        # Use plain Python lists — pandas int64 serialises to a binary typed array
        # that Plotly.js cannot resolve inside template strings.
        item_counts = [int(n) for n in epic_groups["ItemCount"]]
        pt_counts = [int(n) for n in epic_groups["StoryPoints"]]

        item_text = [f"{n} item{'s' if n != 1 else ''}" for n in item_counts]
        pts_text = [f"{n} pts" for n in pt_counts]

        # customdata carries values for hover — more reliable than %{value}
        # when values are passed as typed arrays.
        item_cd = [[n] for n in item_counts]
        pts_cd = [[n] for n in pt_counts]

        hover_items = "%{label}<br>Items: %{customdata[0]}<br>Share: %{percentRoot:.1%}<extra></extra>"
        hover_pts = "%{label}<br>Points: %{customdata[0]}<br>Share: %{percentRoot:.1%}<extra></extra>"

        if not has_story_points:
            fig = go.Figure(
                data=go.Treemap(
                    labels=epic_groups["Epic"].tolist(),
                    parents=[""] * len(epic_groups),
                    values=item_counts,
                    text=item_text,
                    customdata=item_cd,
                    texttemplate="%{label}<br>%{text}",
                    hovertemplate=hover_items,
                    marker=dict(colors=epic_colors, line=dict(width=2, color="#F9F9F7")),
                    name="By item count",
                )
            )
            fig.add_annotation(
                text=(
                    "Story points not available - configure the Story Points"
                    " Field ID in Configuration to enable the right panel"
                ),
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.15,
                showarrow=False,
                font=dict(size=12, color="#2C3E50"),
            )
            fig.update_layout(height=340, margin=dict(t=40, r=16, b=60, l=16))
            return fig.to_json()

        fig = go.Figure()
        fig.add_trace(
            go.Treemap(
                labels=epic_groups["Epic"].tolist(),
                parents=[""] * len(epic_groups),
                values=item_counts,
                text=item_text,
                customdata=item_cd,
                texttemplate="%{label}<br>%{text}",
                hovertemplate=hover_items,
                marker=dict(colors=epic_colors, line=dict(width=2, color="#F9F9F7")),
                name="By item count",
                domain=dict(x=[0, 0.47], y=[0, 1]),
            )
        )
        fig.add_trace(
            go.Treemap(
                labels=epic_groups["Epic"].tolist(),
                parents=[""] * len(epic_groups),
                values=pt_counts,
                text=pts_text,
                customdata=pts_cd,
                texttemplate="%{label}<br>%{text}",
                hovertemplate=hover_pts,
                marker=dict(colors=epic_colors, line=dict(width=2, color="#F9F9F7")),
                name="By story points",
                domain=dict(x=[0.53, 1], y=[0, 1]),
            )
        )
        fig.add_annotation(
            text="By item count",
            x=0.23,
            y=1.05,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=12, color="#2C3E50"),
        )
        fig.add_annotation(
            text="By story points",
            x=0.77,
            y=1.05,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=12, color="#2C3E50"),
        )
        fig.update_layout(height=340, margin=dict(t=40, r=16, b=8, l=16), showlegend=False)
        return fig.to_json()
