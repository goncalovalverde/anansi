import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

logger = logging.getLogger(__name__)

ANANSI_COLORS = ['#007B85', '#F5A623', '#D35400', '#2C3E50', '#5DADE2', '#A569BD', '#52BE80']


class Backlog:
    def __init__(self, cycle_data: pd.DataFrame, config: dict):
        self.cycle_data = cycle_data
        self.config = config
        workflow = config.get("Workflow", [])

        raw_done = workflow[-1] if workflow else "Done"
        self.done_step = self._resolve_step(cycle_data, raw_done, workflow, reversed_order=True)
        if self.done_step != raw_done:
            logger.warning(
                "Configured done step '%s' not found in data. Falling back to '%s'.",
                raw_done, self.done_step,
            )

        raw_in_prog = config.get("start_step") or (workflow[1] if len(workflow) > 1 else "In Progress")
        self.in_progress_step = self._resolve_step(cycle_data, raw_in_prog, workflow, reversed_order=False)
        if self.in_progress_step != raw_in_prog:
            logger.warning(
                "Configured in-progress step '%s' not found in data. Falling back to '%s'.",
                raw_in_prog, self.in_progress_step,
            )

        self.link_ref = (
            '<a href="{}browse/{}" style="cursor:pointer" '
            'target="_blank" rel="noopener noreferrer">{}</a>'
        )
        self.treemap_data = self.get_treemap_data(cycle_data)
        self.treemap_data = self.calculate_cycle_time(self.treemap_data)

    @staticmethod
    def _resolve_step(df: pd.DataFrame, preferred: str, workflow: list, reversed_order: bool) -> str:
        """Return preferred if it is a column in df, otherwise the nearest
        matching column. For done_step (reversed_order=True) common terminal
        names are tried before workflow steps so 'Done' beats 'In Review'."""
        if preferred in df.columns:
            return preferred
        if reversed_order:
            common = ("Done", "Resolved", "Closed", "Completed", "Complete", "Released")
        else:
            common = ("In Progress", "In Development", "In Dev", "Doing", "Active")
        for candidate in common:
            if candidate in df.columns:
                return candidate
        steps = list(reversed(workflow)) if reversed_order else workflow
        for step in steps:
            if step in df.columns:
                return step
        return preferred  # give up — charts will surface their own error

    # ------------------------------------------------------------------ #
    #  Chart methods — each returns a Plotly JSON string                   #
    # ------------------------------------------------------------------ #

    def _normalize_status(self, status: str) -> str:
        """Bucket arbitrary Jira status names into 3 display categories."""
        s = str(status).lower()
        if status == self.done_step or any(k in s for k in ("done", "closed", "resolved", "released", "complete")):
            return "Done"
        if status == self.in_progress_step or any(k in s for k in ("progress", "review", "active", "doing", "development", "dev")):
            return "In Progress"
        return "To Do"

    def draw_treemap(self) -> str:
        """Treemap of completed work only, coloured by Epic."""
        done_data = self.treemap_data[self.treemap_data["Status"] == self.done_step]
        if done_data.empty:
            return go.Figure(
                layout={"title": f"No completed items — Status must be '{self.done_step}' to appear here"}
            ).to_json()
        fig = px.treemap(
            done_data,
            path=["Epic Name", "Type", "Composed"],
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
        )
        fig.update_traces(
            texttemplate="%{label}",
            textinfo="label",
            hovertemplate="%{label}<br>Count: %{value}<br>Parent: %{parent}<extra></extra>",
            textfont_size=11,
            marker_line_width=2,
            marker_line_color="#F9F9F7",
        )
        return fig.to_json()

    def draw_treemap_all(self) -> str:
        """Treemap of all work, coloured by normalized status bucket."""
        df = self.treemap_data.copy()
        if df.empty:
            return go.Figure(layout={"title": "No data available"}).to_json()
        df["Progress"] = df["Status"].apply(self._normalize_status)
        color_map = {
            "Done":        ANANSI_COLORS[0],
            "In Progress": ANANSI_COLORS[1],
            "To Do":       ANANSI_COLORS[3],
        }
        fig = px.treemap(
            df,
            path=["Epic Name", "Type", "Composed"],
            color="Progress",
            color_discrete_map=color_map,
        )
        fig.update_traces(
            texttemplate="%{label}",
            textinfo="label",
            hovertemplate="%{label}<br>Count: %{value}<br>Status: %{color}<br>Parent: %{parent}<extra></extra>",
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
            long, x="Date", y="Epic Name", color="Stage",
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
            return go.Figure(
                layout={"title": "story_points unavailable: Story Points column missing"}
            ).to_json()
        df = self.treemap_data.copy()
        df[sp_col] = pd.to_numeric(df[sp_col], errors="coerce").fillna(0)
        agg = df.groupby("Epic Name", as_index=False)[sp_col].sum()
        if agg[sp_col].sum() == 0:
            return go.Figure(
                layout={"title": "story_points unavailable: No story points data"}
            ).to_json()
        
        # Convert to dict to avoid numpy serialization issues
        agg_dict = agg.to_dict(orient="records")
        
        fig = go.Figure()
        for i, row in enumerate(agg_dict):
            fig.add_trace(go.Bar(
                x=[row["Epic Name"]],
                y=[row[sp_col]],
                name=row["Epic Name"],
                marker=dict(color=ANANSI_COLORS[i % len(ANANSI_COLORS)]),
                legendgroup=row["Epic Name"],
                showlegend=True,
            ))
        
        fig.update_layout(
            xaxis=dict(type="category", tickangle=-30, automargin=True, showticklabels=False),
            barmode="relative",
        )
        return fig.to_json()

    def draw_timeline(self) -> str:
        x_start = self.in_progress_step if self.in_progress_step in self.treemap_data.columns else "Created"
        data = self.treemap_data.dropna(subset=[x_start, self.done_step]).copy()
        
        if data.empty:
            return go.Figure(
                layout={"title": f"No completed items (need '{self.done_step}' dates - check Workflow settings)"}
            ).to_json()
        
        if "Cycle Time" in data.columns and len(data) > 20:
            data = data.nlargest(20, "Cycle Time")
            subtitle = "Showing 20 slowest items by cycle time"
        else:
            subtitle = ""
        
        fig = px.timeline(
            data,
            x_start=x_start,
            x_end=self.done_step,
            y="Summary",
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
            title=subtitle if subtitle else None,
        )
        fig.update_layout(yaxis={"visible": True, "automargin": True})
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

    def draw_issues_by_status(self) -> str:
        """Stacked bar chart: count of issues per status, stacked by issue type, ordered by workflow."""
        df = self.treemap_data.copy()
        if df.empty or "Status" not in df.columns or "Type" not in df.columns:
            return go.Figure(
                layout={"title": "No data — Status and Type columns required"}
            ).to_json()
        
        total_issues = len(df)
        # Drop rows where Status is NaN to get actual issue counts
        df_with_status = df.dropna(subset=["Status"])
        issues_with_status = len(df_with_status)
        
        if df_with_status.empty:
            return go.Figure(
                layout={"title": f"No data — {total_issues} issues found but none have Status assigned"}
            ).to_json()
        
        # Group by status and type, count issues
        grouped = df_with_status.groupby(["Status", "Type"], as_index=False).size()
        grouped.columns = ["Status", "Type", "Count"]
        
        if grouped.empty:
            return go.Figure(
                layout={"title": "No data available"}
            ).to_json()
        
        # Order statuses by workflow configuration
        workflow = self.config.get("Workflow", [])
        status_order = workflow if workflow else sorted(grouped["Status"].unique())
        
        # Create categorical type for proper ordering
        grouped["Status"] = pd.Categorical(grouped["Status"], categories=status_order, ordered=True)
        grouped = grouped.sort_values("Status")
        
        # Create stacked bar chart
        fig = px.bar(
            grouped,
            x="Status",
            y="Count",
            color="Type",
            color_discrete_sequence=ANANSI_COLORS,
            title=f"Issues by Status ({issues_with_status}/{total_issues} with Status)",
            barmode="stack",
        )
        fig.update_layout(
            xaxis=dict(type="category", tickangle=-30, automargin=True),
            yaxis=dict(title="Count"),
        )
        return fig.to_json()

    def draw_timeline_size(self) -> str:
        done_data = self.treemap_data[self.treemap_data["Status"] == self.done_step]
        if done_data.empty:
            return go.Figure(
                layout={"title": f"No data — Status must be '{self.done_step}' to appear here (check Workflow settings)"}
            ).to_json()
        fig = px.scatter(
            done_data,
            x=self.done_step,
            y="Epic Name",
            size="Cycle Time",
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
            title="When things were done and how big",
        )
        return fig.to_json()

    # ------------------------------------------------------------------ #
    #  Aggregate helper                                                    #
    # ------------------------------------------------------------------ #

    def get_all_charts(self) -> dict:
        chart_methods = {
            "treemap":     self.draw_treemap,
            "treemap_all": self.draw_treemap_all,
            "distribution": self.draw_distribution,
            "pbis_done": lambda: self.draw_issues_histogram(self.done_step),
            "pbis_created": lambda: self.draw_issues_histogram("Created"),
            "story_points": self.draw_story_points,
            "timeline": self.draw_timeline,
            "type_issue": self.draw_type_issue,
            "issues_by_status": self.draw_issues_by_status,
            "timeline_size": self.draw_timeline_size,
        }
        results = {}
        for name, method in chart_methods.items():
            try:
                results[name] = method()
            except Exception as exc:
                logger.exception("Chart '%s' failed: %s", name, exc)
                results[name] = go.Figure(
                    layout={"title": f"{name} unavailable: {exc}"}
                ).to_json()
        return results

    def get_kpis(self) -> dict:
        df = self.treemap_data
        total = len(df)
        done_col = self.done_step
        in_progress_col = self.in_progress_step

        done_count = int(df[done_col].notna().sum()) if done_col in df.columns else 0
        in_progress_count = int(df[in_progress_col].notna().sum()) if in_progress_col in df.columns else 0

        avg_cycle = 0.0
        cycle_trend = "neutral"
        if "Cycle Time" in df.columns and done_col in df.columns:
            ct_df = df[[done_col, "Cycle Time"]].dropna()
            ct_df = ct_df[ct_df["Cycle Time"] > 0]
            if len(ct_df) >= 4:
                median_date = ct_df[done_col].median()
                first_half = ct_df[ct_df[done_col] <= median_date]["Cycle Time"]
                second_half = ct_df[ct_df[done_col] > median_date]["Cycle Time"]
                avg_cycle = round(float(ct_df["Cycle Time"].mean()), 1)
                if len(first_half) > 0 and len(second_half) > 0:
                    diff = second_half.mean() - first_half.mean()
                    if diff < -1:
                        cycle_trend = "improving"
                    elif diff > 1:
                        cycle_trend = "worsening"
                    else:
                        cycle_trend = "stable"
            elif len(ct_df) > 0:
                avg_cycle = round(float(ct_df["Cycle Time"].mean()), 1)

        return {
            "total_issues": total,
            "done_count": done_count,
            "in_progress_count": in_progress_count,
            "avg_cycle_time_days": avg_cycle,
            "cycle_trend": cycle_trend,
        }

    def get_insights(self) -> list:
        df = self.treemap_data
        done_col = self.done_step
        in_prog_col = self.in_progress_step
        insights = []

        # 1. Completed count check
        done_count = int(df[done_col].notna().sum()) if done_col in df.columns else 0
        if done_count == 0:
            insights.append({"type": "alert", "message": "No items marked Done - delivery may be stalled"})
        elif done_count > 0:
            insights.append({"type": "ok", "message": f"{done_count} items completed this period"})

        # 2. WIP check
        in_prog = int(df[in_prog_col].notna().sum()) if in_prog_col in df.columns else 0
        if in_prog > 100:
            insights.append({"type": "alert", "message": f"High WIP - {in_prog} items active simultaneously"})
        elif in_prog > 50:
            insights.append({"type": "warn", "message": f"WIP is elevated ({in_prog} items) - consider limiting parallel work"})

        # 3. Cycle time check
        if "Cycle Time" in df.columns and done_count > 0:
            ct = df["Cycle Time"].dropna()
            ct = ct[ct > 0]
            if len(ct) > 0:
                avg = round(float(ct.mean()), 1)
                if avg > 30:
                    insights.append({"type": "warn", "message": f"Average cycle time is {avg} days - items are taking over a month to complete"})
                elif avg <= 10:
                    insights.append({"type": "ok", "message": f"Cycle time is healthy at {avg} days on average"})

        # 4. Bug ratio check
        bug_types = {"bug", "defect"}
        if "Type" in df.columns:
            total = len(df)
            bugs = df["Type"].str.lower().isin(bug_types).sum()
            if total > 0:
                ratio = round(bugs / total * 100, 1)
                if ratio > 30:
                    insights.append({"type": "alert", "message": f"Bug ratio is {ratio}% - quality issues may be affecting delivery"})
                elif ratio > 15:
                    insights.append({"type": "warn", "message": f"Bug ratio is {ratio}% - worth monitoring"})

        # 5. Backlog growth (created dates)
        if "Created" in df.columns:
            created = df["Created"].dropna()
            if len(created) > 0:
                mid = created.median()
                first_half = (created <= mid).sum()
                second_half = (created > mid).sum()
                if first_half > 0 and second_half > first_half * 1.2:
                    pct = round((second_half - first_half) / first_half * 100)
                    insights.append({"type": "warn", "message": f"Backlog grew {pct}% this period - more is being added than completed"})
                elif second_half < first_half:
                    insights.append({"type": "ok", "message": "Backlog is shrinking - good sign of delivery focus"})

        # Sort: alert first, then warn, then ok; cap at 5
        order = {"alert": 0, "warn": 1, "ok": 2}
        insights.sort(key=lambda x: order.get(x["type"], 3))
        return insights[:5]

    def get_callouts(self) -> dict:
        df = self.treemap_data
        done_col = self.done_step
        callouts = {}

        # treemap
        done_data = df[df["Status"] == done_col]
        if done_data.empty:
            callouts["treemap"] = {"message": "No completed work to display - items may not be reaching Done status", "severity": "alert"}
        else:
            n_epics = done_data["Epic Name"].nunique()
            if n_epics == 1:
                callouts["treemap"] = {"message": "Only 1 epic has completed items - are other epics blocked or not yet started?", "severity": "warn"}

        # pbis_done
        done_count = int(df[done_col].notna().sum()) if done_col in df.columns else 0
        if done_count == 0:
            callouts["pbis_done"] = {"message": "No items completed in this period", "severity": "alert"}

        # story_points
        sp_col = "Story Points"
        if sp_col not in df.columns or pd.to_numeric(df[sp_col], errors="coerce").fillna(0).sum() == 0:
            callouts["story_points"] = {"message": "No story points recorded - check that story point field ID is configured correctly", "severity": "warn"}
        else:
            by_epic = df.groupby("Epic Name")[sp_col].apply(lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum())
            total_sp = by_epic.sum()
            if total_sp > 0:
                top_pct = by_epic.max() / total_sp
                if top_pct > 0.6:
                    callouts["story_points"] = {"message": "One epic is consuming most delivery capacity - other areas may be under-resourced", "severity": "warn"}

        # type_issue - bug ratio
        if "Type" in df.columns:
            total = len(df)
            bug_types = {"bug", "defect"}
            bugs = df["Type"].str.lower().isin(bug_types).sum()
            if total > 0:
                ratio = round(bugs / total * 100, 1)
                if ratio > 25:
                    callouts["type_issue"] = {"message": f"High defect ratio ({ratio}%) - more than 1 in 4 items is a bug or defect", "severity": "alert"}
                elif bugs == 0:
                    callouts["type_issue"] = {"message": "No bugs or defects in this period", "severity": "ok"}

        # timeline - slowest item
        if "Cycle Time" in df.columns and done_col in df.columns:
            ct_df = df[df[done_col].notna() & df["Cycle Time"].notna() & (df["Cycle Time"] > 0)]
            if not ct_df.empty:
                avg_ct = ct_df["Cycle Time"].mean()
                max_row = ct_df.loc[ct_df["Cycle Time"].idxmax()]
                max_ct = int(max_row["Cycle Time"])
                if max_ct > 60:
                    name = str(max_row.get("Summary", "An item"))[:50]
                    callouts["timeline"] = {"message": f"{name} has been in progress for {max_ct} days", "severity": "alert"}
                elif avg_ct > 30:
                    callouts["timeline"] = {"message": f"Average item age is {round(avg_ct)} days - consider breaking work into smaller pieces", "severity": "warn"}

        # timeline_size - outliers (> 3x average)
        if "Cycle Time" in df.columns:
            ct_vals = df["Cycle Time"].dropna()
            ct_vals = ct_vals[ct_vals > 0]
            if len(ct_vals) > 0:
                avg_ct = ct_vals.mean()
                outliers = (ct_vals > 3 * avg_ct).sum()
                if outliers > 0:
                    callouts["timeline_size"] = {"message": f"{outliers} item{'s' if outliers > 1 else ''} took more than 3 times the average to complete", "severity": "warn"}

        return callouts

    def draw_flow_efficiency(self) -> str:
        df = self.treemap_data
        done_col = self.done_step
        in_prog_col = self.in_progress_step
        done_data = df[df["Status"] == done_col]
        if done_data.empty or "Cycle Time" not in df.columns:
            return go.Figure(layout={"title": "flow_efficiency unavailable: No completed items"}).to_json()
        done_count = len(done_data)
        in_prog_count = int(df[in_prog_col].notna().sum()) if in_prog_col in df.columns else 0
        total = done_count + in_prog_count
        efficiency = round(done_count / total * 100, 1) if total > 0 else 0
        color = "#52BE80" if efficiency > 40 else ("#F5A623" if efficiency >= 20 else "#D35400")
        fig = go.Figure(go.Indicator(
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
        ))
        return fig.to_json()

    def draw_wip_trend(self) -> str:
        df = self.treemap_data
        in_prog_col = self.in_progress_step
        done_col = self.done_step
        if in_prog_col not in df.columns:
            return go.Figure(layout={"title": "wip_trend unavailable: No in-progress date column"}).to_json()
        started = df[in_prog_col].dropna()
        if started.empty:
            return go.Figure(layout={"title": "wip_trend unavailable: No in-progress data"}).to_json()
        date_min = started.min()
        date_max = max(
            started.max(),
            df[done_col].dropna().max() if done_col in df.columns else started.max()
        )
        weeks = pd.date_range(start=date_min, end=date_max, freq="W")
        wip_counts = []
        for week_end in weeks:
            in_prog = df[in_prog_col].notna() & (df[in_prog_col] <= week_end)
            if done_col in df.columns:
                not_done = df[done_col].isna() | (df[done_col] > week_end)
            else:
                not_done = pd.Series([True] * len(df))
            count = (in_prog & not_done).sum()
            wip_counts.append({"week": week_end, "wip": int(count)})
        wip_df = pd.DataFrame(wip_counts)
        if wip_df.empty:
            return go.Figure(layout={"title": "wip_trend unavailable: No data"}).to_json()
        color = ANANSI_COLORS[2] if (len(wip_df) >= 4 and wip_df["wip"].iloc[-4:].mean() > wip_df["wip"].iloc[-8:-4].mean() * 1.2) else ANANSI_COLORS[0]
        fig = go.Figure(go.Scatter(x=wip_df["week"], y=wip_df["wip"], mode="lines+markers", line={"color": color, "width": 2}, name="WIP"))
        fig.update_layout(xaxis={"title": "Week"}, yaxis={"title": "Items in Progress"})
        return fig.to_json()

    def draw_throughput(self) -> str:
        df = self.treemap_data
        done_col = self.done_step
        if done_col not in df.columns:
            return go.Figure(layout={"title": "throughput unavailable: No done date column"}).to_json()
        done_dates = df[done_col].dropna()
        if done_dates.empty:
            return go.Figure(layout={"title": "throughput unavailable: No completed items"}).to_json()
        weekly = done_dates.dt.to_period("W").value_counts().sort_index()
        weeks = [str(p.start_time.date()) for p in weekly.index]
        counts = weekly.values.tolist()
        rolling = pd.Series(counts).rolling(4, min_periods=1).mean().round(1).tolist()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=weeks, y=counts, name="Completed", marker_color=ANANSI_COLORS[0]))
        fig.add_trace(go.Scatter(x=weeks, y=rolling, mode="lines", name="4-week avg", line={"color": ANANSI_COLORS[1], "width": 2, "dash": "dot"}))
        fig.update_layout(xaxis={"type": "category", "tickangle": -30}, yaxis={"title": "Items completed"})
        return fig.to_json()

    def draw_cumulative_flow(self) -> str:
        df = self.treemap_data
        done_col = self.done_step
        created_col = "Created"
        if created_col not in df.columns:
            return go.Figure(layout={"title": "cumulative_flow unavailable: No Created date column"}).to_json()
        created = df[created_col].dropna()
        done_dates = df[done_col].dropna() if done_col in df.columns else pd.Series([], dtype="datetime64[ns]")
        if created.empty:
            return go.Figure(layout={"title": "cumulative_flow unavailable: No date data"}).to_json()
        date_min = created.min()
        date_max = max(created.max(), done_dates.max() if len(done_dates) > 0 else created.max())
        dates = pd.date_range(start=date_min, end=date_max, freq="W")
        cum_created = [(d, int((created <= d).sum())) for d in dates]
        cum_done = [(d, int((done_dates <= d).sum())) for d in dates] if len(done_dates) > 0 else [(d, 0) for d in dates]
        xs = [str(d.date()) for d in dates]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xs, y=[c[1] for c in cum_created], mode="lines", name="Created", line={"color": ANANSI_COLORS[1], "width": 2}, fill="tonexty", fillcolor="rgba(0,123,133,0.1)"))
        fig.add_trace(go.Scatter(x=xs, y=[c[1] for c in cum_done], mode="lines", name="Completed", line={"color": ANANSI_COLORS[0], "width": 2}))
        fig.update_layout(xaxis={"tickformat": "%b %Y", "tickangle": -30}, yaxis={"title": "Cumulative items"})
        return fig.to_json()

    def draw_monthly_throughput(self) -> str:
        df = self.treemap_data
        done_col = self.done_step
        if done_col not in df.columns:
            return go.Figure(layout={"title": "monthly_throughput unavailable: No done date"}).to_json()
        done_dates = df[done_col].dropna()
        if done_dates.empty:
            return go.Figure(layout={"title": "monthly_throughput unavailable: No completed items"}).to_json()
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
        fig.add_trace(go.Scatter(x=xs, y=trend, mode="lines", name="Trend", line={"color": ANANSI_COLORS[2], "width": 2, "dash": "dot"}))
        fig.update_layout(xaxis={"type": "category", "tickangle": -30}, yaxis={"title": "Items completed"})
        return fig.to_json()

    def draw_epic_progress(self) -> str:
        df = self.treemap_data
        done_col = self.done_step
        if done_col not in df.columns:
            return go.Figure(layout={"title": "epic_progress unavailable: No done date"}).to_json()
        done_data = df[df["Status"] == done_col].copy()
        epic_groups = done_data.groupby("Epic Name")[done_col]
        epic_first = epic_groups.min().dropna()
        epic_last = epic_groups.max().dropna()
        epic_count = done_data.groupby("Epic Name").size()
        epics = sorted(set(epic_first.index) & set(epic_last.index))
        if not epics:
            return go.Figure(layout={"title": "epic_progress unavailable: No completed items"}).to_json()
        epic_data = []
        for epic in epics:
            epic_data.append({
                "Epic": epic,
                "Start": epic_first[epic],
                "End": epic_last[epic],
                "Count": int(epic_count.get(epic, 1)),
            })
        epic_df = pd.DataFrame(epic_data)
        fig = px.timeline(epic_df, x_start="Start", x_end="End", y="Epic", color="Epic",
                          color_discrete_sequence=ANANSI_COLORS)
        fig.update_layout(showlegend=False, yaxis={"automargin": True})
        return fig.to_json()

    # ------------------------------------------------------------------ #
    #  Data preparation                                                    #
    # ------------------------------------------------------------------ #

    def get_treemap_data(self, df: pd.DataFrame) -> pd.DataFrame:
        non_epics = df.query('Type != "Epic"')
        epics = df.query('Type == "Epic"')
        epics = epics.rename(columns={"Key": "Epic Key", "Summary": "Epic Name"})

        # Convert "No Epic" to NaN so merge treats it as missing instead of a literal key
        non_epics = non_epics.copy()
        non_epics.loc[non_epics["Epic Link"] == "No Epic", "Epic Link"] = None

        merged = pd.merge(
            non_epics,
            epics[["Epic Key", "Epic Name"]],
            left_on="Epic Link",
            right_on="Epic Key",
            how="left",
        )
        # When Epic issues are in the dataset their Summary becomes the Epic Name.
        # When they are not fetched (e.g. JQL filters to Stories/Bugs/Tasks only),
        # fall back to the raw Epic Link key so grouping still works meaningfully
        # rather than collapsing everything into "No Epic".
        merged["Epic Name"] = (
            merged["Epic Name"]
            .fillna(merged.get("Epic Link"))
            .fillna("No Epic")
        )

        jira_url = self.config.get("jira", {}).get("url", "")
        merged["Key"] = merged["Key"].apply(
            lambda item: self.link_ref.format(jira_url, item, item)
        )
        merged["Composed"] = merged["Summary"] + "\n" + merged["Key"]

        # Parse all date columns once at load time so every chart receives
        # proper datetime64 types and never needs to re-coerce.
        date_cols = {"Created"} | set(self.config.get("Workflow", []))
        for col in date_cols:
            if col in merged.columns:
                merged[col] = pd.to_datetime(merged[col], errors="coerce")
        return merged

    def calculate_cycle_time(self, treemap_data: pd.DataFrame) -> pd.DataFrame:
        # Cycle time = Done date - Created date (how long from creation to completion)
        if self.done_step in treemap_data.columns and "Created" in treemap_data.columns:
            treemap_data["Cycle Time"] = pd.to_numeric(
                (treemap_data[self.done_step] - treemap_data["Created"]).dt.days,
                downcast="integer",
            )
        else:
            treemap_data["Cycle Time"] = 0
        treemap_data["Cycle Time"] = treemap_data["Cycle Time"].fillna(0)
        return treemap_data
