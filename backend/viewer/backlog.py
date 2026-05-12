import json
import logging
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Optional, Dict, List

from .backlog_data import BacklogData
from .chart_config import ANANSI_COLORS, ChartConfig, EpicColorMap  # re-exported for callers
from .chart_helpers import _create_empty_state_figure               # re-exported for callers
from .backlog_charts import BacklogChartsMixin
from .backlog_insights import BacklogInsightsMixin
from .flow_charts import FlowChartsMixin
from .trend_charts import TrendChartsMixin

logger = logging.getLogger(__name__)


class Backlog(BacklogInsightsMixin, BacklogChartsMixin, FlowChartsMixin, TrendChartsMixin):
    def __init__(self, cycle_data: pd.DataFrame, config: dict):
        self.cycle_data = cycle_data
        self.config = config
        self.chart_config = ChartConfig(config.get("chart_thresholds"))
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

        # Guard: in_progress_step must not equal done_step (e.g. 2-step workflow
        # where workflow[1] == done step). Re-resolve against common names then
        # the first non-done workflow column.
        if self.in_progress_step == self.done_step:
            fallback = None
            for candidate in ("In Progress", "In Development", "In Dev", "Doing", "Active"):
                if candidate in cycle_data.columns and candidate != self.done_step:
                    fallback = candidate
                    break
            if fallback is None:
                for step in workflow:
                    if step in cycle_data.columns and step != self.done_step:
                        fallback = step
                        break
            if fallback:
                logger.warning(
                    "in_progress_step resolved to done_step '%s'. Using '%s' instead.",
                    self.done_step, fallback,
                )
                self.in_progress_step = fallback

        self.link_ref = (
            '<a href="{}browse/{}" style="cursor:pointer" '
            'target="_blank" rel="noopener noreferrer">{}</a>'
        )
        self.raw_data = cycle_data.copy()  # Store raw unfiltered data for charts like issues_by_status
        self.treemap_data = self.get_treemap_data(cycle_data)
        self.treemap_data = self.calculate_cycle_time(self.treemap_data)

        self.data = BacklogData.from_cycle_data(self.treemap_data, self.done_step)

        # Convenience aliases — chart methods access these directly; no refactor needed.
        self._done_df = self.data.done_df
        self._active_df = self.data.active_df
        self._ct_df = self.data.ct_df

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
    #  Status classification (used by mixin chart methods via self)        #
    # ------------------------------------------------------------------ #

    def _normalize_status(self, status: str) -> str:
        """Bucket arbitrary Jira status names into 3 display categories."""
        s = str(status).lower()
        if status == self.done_step or any(k in s for k in ("done", "closed", "resolved", "released", "complete")):
            return "Done"
        if status == self.in_progress_step or any(k in s for k in ("progress", "review", "active", "doing", "development", "dev")):
            return "In Progress"
        return "To Do"

    # ------------------------------------------------------------------ #
    #  Aggregate helper                                                    #
    # ------------------------------------------------------------------ #

    def get_all_charts(self) -> dict:
        """Generate all dashboard charts. Returns a dict of parsed Plotly dicts
        (not JSON strings) so the API layer avoids a redundant encode/decode."""
        chart_methods = {
            "treemap":        self.draw_treemap,
            "treemap_all":    self.draw_treemap_all,
            "distribution":   self.draw_distribution,
            "pbis_done":      lambda: self.draw_issues_histogram(self.done_step),
            "pbis_created":   lambda: self.draw_issues_histogram("Created"),
            "story_points":   self.draw_story_points,
            "type_issue":     self.draw_type_issue,
            "timeline_size":  self.draw_timeline_size,
            "aging_heatmap":  self.draw_aging_heatmap,
            "epic_investment": self.draw_epic_investment,
        }
        results = {}
        for name, method in chart_methods.items():
            try:
                results[name] = json.loads(method())
            except Exception as exc:
                logger.exception("Chart '%s' failed: %s", name, exc)
                results[name] = json.loads(
                    go.Figure(layout={"title": f"{name} unavailable: {exc}"}).to_json()
                )
        return results

    def get_flow_charts(self) -> dict:
        """Generate all Flow tab charts. Returns parsed Plotly dicts."""
        flow_methods = {
            "flow_efficiency":      self.draw_flow_efficiency,
            "wip_trend":            self.draw_wip_trend,
            "throughput_histogram": self.draw_throughput_histogram,
            "distribution":         self.draw_distribution,
            "timeline_size":        self.draw_timeline_size,
        }
        results = {}
        for name, method in flow_methods.items():
            try:
                results[name] = json.loads(method())
            except Exception as exc:
                logger.error("Chart '%s' failed: %s", name, exc, exc_info=True)
                results[name] = json.loads(
                    go.Figure(layout={"title": f"{name} unavailable"}).to_json()
                )
        return results

    def get_kpis(self) -> dict:
        df = self.treemap_data
        total = len(df)
        in_progress_col = self.in_progress_step

        done_count = len(self._done_df)
        if "Status" in df.columns:
            in_progress_count = int(
                (df["Status"].apply(self._normalize_status) == "In Progress").sum()
            )
        else:
            in_progress_count = int(df[in_progress_col].notna().sum()) if in_progress_col in df.columns else 0

        avg_cycle = 0.0
        cycle_trend = "neutral"
        ct_df = self._ct_df
        if not ct_df.empty:
            done_col = self.done_step
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
            else:
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
        # Filter to configured issue types to track
        configured_types = self.config.get("issue_type", [])
        if configured_types and "Total" in configured_types:
            # Remove "Total" (it's just a label) and filter to the rest
            filtered_types = [t for t in configured_types if t != "Total"]
            if filtered_types:
                df = df[df["Type"].isin(filtered_types)].copy()
                logger.info(f"Filtered to tracked types: {filtered_types}, {len(df)} issues remaining")
        
        non_epics = df.query('Type != "Epic"')
        epics = df.query('Type == "Epic"')
        epics = epics.rename(columns={"Key": "Epic Key", "Summary": "Epic Name"})

        logger.info(f"Data load: {len(non_epics)} non-epics, {len(epics)} epics")
        
        # Convert "No Epic" to NaN so merge treats it as missing instead of a literal key
        non_epics = non_epics.copy()
        original_no_epic = (non_epics["Epic Link"] == "No Epic").sum()
        non_epics.loc[non_epics["Epic Link"] == "No Epic", "Epic Link"] = None
        
        # Check which non-epics have an Epic Link value
        has_epic_link = non_epics["Epic Link"].notna().sum()
        logger.info(f"Epic Links: {has_epic_link} issues linked to epics, {original_no_epic} with 'No Epic'")

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
        
        epic_dist = merged["Epic Name"].value_counts()
        logger.info(f"Epic distribution after merge: {epic_dist.to_dict()}")

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
