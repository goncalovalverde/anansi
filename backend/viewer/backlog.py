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
        self.done_step = workflow[-1] if workflow else "Done"
        self.in_progress_step = config.get("start_step") or (workflow[1] if len(workflow) > 1 else "In Progress")
        self.link_ref = (
            '<a href="{}browse/{}" style="cursor:pointer" '
            'target="_blank" rel="noopener noreferrer">{}</a>'
        )
        self.treemap_data = self.get_treemap_data(cycle_data)
        self.treemap_data = self.calculate_cycle_time(self.treemap_data)

    # ------------------------------------------------------------------ #
    #  Chart methods — each returns a Plotly JSON string                   #
    # ------------------------------------------------------------------ #

    def draw_treemap(self) -> str:
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

    def draw_distribution(self) -> str:
        date_cols = [c for c in [self.done_step, self.in_progress_step] if c in self.treemap_data.columns]
        df = self.treemap_data[["Epic Name"] + date_cols].copy()
        for c in date_cols:
            df[c] = pd.to_datetime(df[c], errors="coerce")
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
        fig = px.histogram(
            self.treemap_data,
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
        fig = px.bar(
            agg,
            x="Epic Name",
            y=sp_col,
            color="Epic Name",
            color_discrete_sequence=ANANSI_COLORS,
        )
        fig.update_layout(xaxis=dict(type="category", tickangle=-30, automargin=True))
        return fig.to_json()

    def draw_timeline(self) -> str:
        x_start = self.in_progress_step if self.in_progress_step in self.treemap_data.columns else "Created"
        data = self.treemap_data.dropna(subset=[x_start, self.done_step]).copy()
        if "Cycle Time" in data.columns and len(data) > 20:
            data = data.nlargest(20, "Cycle Time")
            subtitle = "Showing 20 slowest items by cycle time"
        else:
            subtitle = ""
        if data.empty:
            return go.Figure(layout={"title": "No completed items"}).to_json()
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

    def draw_timeline_size(self) -> str:
        done_data = self.treemap_data[self.treemap_data["Status"] == self.done_step]
        if done_data.empty:
            return go.Figure(
                layout={"title": f"No completed items — Status must be '{self.done_step}' to appear here"}
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
            "treemap": self.draw_treemap,
            "distribution": self.draw_distribution,
            "pbis_done": lambda: self.draw_issues_histogram(self.done_step),
            "pbis_created": lambda: self.draw_issues_histogram("Created"),
            "story_points": self.draw_story_points,
            "timeline": self.draw_timeline,
            "type_issue": self.draw_type_issue,
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
        import datetime
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
                import pandas as pd
                created = pd.to_datetime(created, errors="coerce").dropna()
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
        import pandas as pd
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

    # ------------------------------------------------------------------ #
    #  Data preparation                                                    #
    # ------------------------------------------------------------------ #

    def get_treemap_data(self, df: pd.DataFrame) -> pd.DataFrame:
        non_epics = df.query('Type != "Epic"')
        epics = df.query('Type == "Epic"')
        epics = epics.rename(columns={"Key": "Epic Key", "Summary": "Epic Name"})

        merged = pd.merge(
            non_epics,
            epics[["Epic Key", "Epic Name"]],
            left_on="Epic Link",
            right_on="Epic Key",
            how="left",
        )
        merged["Epic Name"] = merged["Epic Name"].fillna("No Epic")

        jira_url = self.config.get("jira", {}).get("url", "")
        merged["Key"] = merged["Key"].apply(
            lambda item: self.link_ref.format(jira_url, item, item)
        )
        merged["Composed"] = merged["Summary"] + "\n" + merged["Key"]
        return merged

    def calculate_cycle_time(self, treemap_data: pd.DataFrame) -> pd.DataFrame:
        if self.done_step in treemap_data.columns and self.in_progress_step in treemap_data.columns:
            treemap_data["Cycle Time"] = pd.to_numeric(
                (treemap_data[self.done_step] - treemap_data[self.in_progress_step]).dt.days,
                downcast="integer",
            )
        else:
            treemap_data["Cycle Time"] = 0
        treemap_data["Cycle Time"] = treemap_data["Cycle Time"].fillna(0)
        return treemap_data
