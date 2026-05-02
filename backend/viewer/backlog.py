import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

logger = logging.getLogger(__name__)


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
        )
        return fig.to_json()

    def draw_distribution(self) -> str:
        date_cols = [c for c in [self.done_step, self.in_progress_step] if c in self.treemap_data.columns]
        df = self.treemap_data[["Epic Name"] + date_cols].copy()
        for c in date_cols:
            df[c] = pd.to_datetime(df[c], errors="coerce")
        long = df.melt(id_vars="Epic Name", value_vars=date_cols, var_name="Stage", value_name="Date")
        long = long.dropna(subset=["Date"])
        fig = px.scatter(
            long, x="Date", y="Epic Name", color="Stage",
            title=f"{self.done_step} and {self.in_progress_step} dates",
        )
        return fig.to_json()

    def draw_pbis_epic(self, status: str) -> str:
        fig = px.histogram(
            self.treemap_data,
            x=[status],
            title=f"{status} PBI's per Epic",
            color="Epic Name",
        )
        return fig.to_json()

    def draw_story_points(self) -> str:
        fig = px.histogram(
            self.treemap_data,
            x=["Story Points"],
            title="Story points delivered",
            color="Epic Name",
        )
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
            title=subtitle if subtitle else None,
        )
        fig.update_layout(yaxis={"visible": True, "automargin": True})
        return fig.to_json()

    def draw_type_issue(self) -> str:
        fig = px.histogram(
            self.treemap_data,
            x=["Type"],
            title="Type of issue",
            color="Epic Name",
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
            x=[self.done_step],
            y="Epic Name",
            size="Cycle Time",
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
            "pbis_done": lambda: self.draw_pbis_epic(self.done_step),
            "pbis_created": lambda: self.draw_pbis_epic("Created"),
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
