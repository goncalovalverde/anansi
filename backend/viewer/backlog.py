import json
import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Optional, Dict, List

from viewer.backlog_data import BacklogData
from viewer.chart_config import ANANSI_COLORS, ChartConfig, EpicColorMap  # re-exported for callers
from viewer.chart_helpers import _create_empty_state_figure               # re-exported for callers
from viewer.backlog_charts import BacklogChartsMixin
from viewer.flow_charts import FlowChartsMixin
from viewer.trend_charts import TrendChartsMixin

logger = logging.getLogger(__name__)


class Backlog(BacklogChartsMixin, FlowChartsMixin, TrendChartsMixin):
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

    def get_insights(self) -> list:
        df = self.treemap_data
        in_prog_col = self.in_progress_step
        insights = []

        # 1. Completed count check — use pre-computed _done_df
        done_count = len(self._done_df)
        if done_count == 0:
            insights.append({"type": "alert", "message": "No items marked Done - delivery may be stalled"})
        else:
            insights.append({"type": "ok", "message": f"{done_count} items completed this period"})

        # 2. WIP check
        in_prog = int(df[in_prog_col].notna().sum()) if in_prog_col in df.columns else 0
        if in_prog > ChartConfig.WIP_HIGH_THRESHOLD:
            insights.append({"type": "alert", "message": f"High WIP - {in_prog} items active simultaneously"})
        elif in_prog > ChartConfig.WIP_ELEVATED_THRESHOLD:
            insights.append({"type": "warn", "message": f"WIP is elevated ({in_prog} items) - consider limiting parallel work"})

        # 3. Cycle time check — use pre-computed _ct_df (done + valid cycle time)
        if not self._ct_df.empty:
            avg = round(float(self._ct_df["Cycle Time"].mean()), 1)
            if avg > ChartConfig.CYCLE_TIME_HIGH_DAYS:
                insights.append({"type": "warn", "message": f"Average cycle time is {avg} days - items are taking over a month to complete"})
            elif avg <= ChartConfig.CYCLE_TIME_HEALTHY_DAYS:
                insights.append({"type": "ok", "message": f"Cycle time is healthy at {avg} days on average"})

        # 4. Bug ratio check
        if "Type" in df.columns:
            total = len(df)
            bugs = df["Type"].str.lower().isin({"bug", "defect"}).sum()
            if total > 0:
                ratio = round(bugs / total * 100, 1)
                if ratio > ChartConfig.BUG_RATIO_HIGH_PCT:
                    insights.append({"type": "alert", "message": f"Bug ratio is {ratio}% - quality issues may be affecting delivery"})
                elif ratio > ChartConfig.BUG_RATIO_ELEVATED_PCT:
                    insights.append({"type": "warn", "message": f"Bug ratio is {ratio}% - worth monitoring"})

        # 5. Backlog growth — use pre-computed _active_df for current backlog
        if "Created" in df.columns:
            created = df["Created"].dropna()
            if len(created) > 0:
                mid = created.median()
                first_half = (created <= mid).sum()
                second_half = (created > mid).sum()
                if first_half > 0 and second_half > first_half * ChartConfig.BACKLOG_GROWTH_RATIO:
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
        callouts = {}
        done_data = self._done_df
        active_df = self._active_df
        ct_df = self._ct_df

        # treemap
        if done_data.empty:
            callouts["treemap"] = {"message": "No completed work to display - items may not be reaching Done status", "severity": "alert"}
        else:
            n_epics = done_data["Epic Name"].nunique()
            if n_epics == 1:
                callouts["treemap"] = {"message": "Only 1 epic has completed items - are other epics blocked or not yet started?", "severity": "warn"}

        # pbis_done
        if done_data.empty:
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
                if top_pct > ChartConfig.CALLOUT_EPIC_CONCENTRATION_PCT:
                    callouts["story_points"] = {"message": "One epic is consuming most delivery capacity - other areas may be under-resourced", "severity": "warn"}

        # type_issue - bug ratio
        if "Type" in df.columns:
            total = len(df)
            bug_types = {"bug", "defect"}
            bugs = df["Type"].str.lower().isin(bug_types).sum()
            if total > 0:
                ratio = round(bugs / total * 100, 1)
                if ratio > ChartConfig.CALLOUT_BUG_RATIO_HIGH_PCT:
                    callouts["type_issue"] = {"message": f"High defect ratio ({ratio}%) - more than 1 in 4 items is a bug or defect", "severity": "alert"}
                elif bugs == 0:
                    callouts["type_issue"] = {"message": "No bugs or defects in this period", "severity": "ok"}

        # timeline - use pre-computed ct_df
        if not ct_df.empty:
            avg_ct = ct_df["Cycle Time"].mean()
            max_row = ct_df.loc[ct_df["Cycle Time"].idxmax()]
            max_ct = int(max_row["Cycle Time"])
            if max_ct > ChartConfig.CALLOUT_CYCLE_TIME_ALERT_DAYS:
                name = str(max_row.get("Summary", "An item"))[:50]
                callouts["timeline_size"] = {"message": f"{name} has been in progress for {max_ct} days", "severity": "alert"}
            elif avg_ct > ChartConfig.CALLOUT_CYCLE_TIME_WARN_DAYS:
                callouts["timeline_size"] = {"message": f"Average item age is {round(avg_ct)} days - consider breaking work into smaller pieces", "severity": "warn"}
            else:
                outliers = (ct_df["Cycle Time"] > ChartConfig.CALLOUT_OUTLIER_CT_MULTIPLIER * avg_ct).sum()
                if outliers > 0:
                    label = "items" if outliers > 1 else "item"
                    callouts["timeline_size"] = {"message": f"{outliers} {label} took more than {ChartConfig.CALLOUT_OUTLIER_CT_MULTIPLIER}x the average to complete", "severity": "warn"}

        # aging_heatmap - use pre-computed active_df
        if not active_df.empty and "Created" in active_df.columns:
            today = pd.Timestamp(datetime.now().date())
            created = pd.to_datetime(active_df["Created"], errors="coerce")
            age_days = (today - created).dt.days.fillna(0)

            old_counts = active_df[age_days >= ChartConfig.AGING_CRITICAL_DAYS].groupby("Epic Name").size()
            if not old_counts.empty:
                worst_epic = old_counts.idxmax()
                worst_count = int(old_counts[worst_epic])
                if worst_count > ChartConfig.AGING_CRITICAL_COUNT:
                    callouts["aging_heatmap"] = {"message": f"{worst_epic} has {worst_count} items older than {ChartConfig.AGING_CRITICAL_DAYS} days - these may be blocked or forgotten", "severity": "alert"}
                else:
                    month_mask = (age_days >= ChartConfig.AGING_WARNING_DAYS) & (age_days < ChartConfig.AGING_CRITICAL_DAYS)
                    month_total = int(month_mask.sum())
                    if month_total > ChartConfig.AGING_WARNING_COUNT:
                        callouts["aging_heatmap"] = {"message": f"{month_total} items are between {ChartConfig.AGING_WARNING_DAYS}-{ChartConfig.AGING_CRITICAL_DAYS} days old - review before they become critical", "severity": "warn"}
                    else:
                        callouts["aging_heatmap"] = {"message": "Backlog age is healthy - no major stale item clusters detected", "severity": "ok"}

        # epic_investment
        epic_groups = df.groupby("Epic Name").agg({
            "Key": "count",
            "Story Points": lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum(),
        }).reset_index()
        epic_groups.columns = ["Epic", "ItemCount", "StoryPoints"]
        epic_groups = epic_groups[epic_groups["ItemCount"] > 0]

        if not epic_groups.empty:
            has_story_points = epic_groups["StoryPoints"].sum() > 0
            if not has_story_points:
                callouts["epic_investment"] = {"message": "Story points not configured - add your Story Points Field ID in Configuration to unlock this view", "severity": "warn"}
            else:
                epic_groups["complexity"] = epic_groups["StoryPoints"] / epic_groups["ItemCount"]
                high_complexity = epic_groups.loc[epic_groups["complexity"].idxmax()]
                low_complexity = epic_groups.loc[epic_groups["complexity"].idxmin()]
                complexity_ratio = (
                    high_complexity["complexity"] / low_complexity["complexity"]
                    if low_complexity["complexity"] > 0 else 0
                )
                if complexity_ratio > ChartConfig.COMPLEXITY_RATIO_THRESHOLD:
                    high_name = high_complexity["Epic"]
                    low_name = low_complexity["Epic"]
                    high_avg = round(high_complexity["complexity"], 1)
                    low_avg = round(low_complexity["complexity"], 1)
                    callouts["epic_investment"] = {"message": f"{high_name} items average {high_avg} points each vs {low_avg} for {low_name} - large complexity gap between epics", "severity": "warn"}

        return callouts

    def get_flow_callouts(self) -> dict:
        """Callouts for Flow tab charts (throughput histogram).
        Returns the same structure as get_callouts() but for flow-specific charts.
        Keeps this logic in the backend so FlowView doesn't re-derive it from chart data.
        """
        callouts = {}

        # Use pre-computed _done_df — avoids re-filtering treemap_data
        if self._done_df.empty:
            callouts["throughput_histogram"] = {
                "message": "No completed items yet - data will appear once items reach Done status",
                "severity": "warn",
            }
            return callouts

        done_col = self.done_step
        done_dates = pd.to_datetime(self._done_df[done_col], errors="coerce").dropna()
        if done_dates.empty:
            callouts["throughput_histogram"] = {
                "message": "No completed items yet - data will appear once items reach Done status",
                "severity": "warn",
            }
            return callouts

        weekly = done_dates.dt.to_period("W").value_counts().sort_index()
        if weekly.empty:
            return callouts

        min_week = weekly.index.min()
        max_week = weekly.index.max()
        all_weeks = pd.period_range(min_week, max_week, freq="W")
        complete_weekly = pd.Series(0, index=all_weeks)
        complete_weekly.update(weekly)
        counts = complete_weekly.values.tolist()

        non_zero = [c for c in counts if c > 0]
        if not non_zero:
            return callouts

        mean = float(np.mean(non_zero))
        stddev = float(np.std(non_zero))
        last_four = counts[-4:] if len(counts) >= 4 else counts
        max_ever = max(counts)
        last_week = counts[-1]

        if len(last_four) == 4 and all(c < mean for c in last_four):
            callouts["throughput_histogram"] = {
                "message": "Delivery has slowed over the last 4 weeks - check for blockers or holiday periods",
                "severity": "warn",
            }
        elif last_week == max_ever and last_week > 0:
            callouts["throughput_histogram"] = {
                "message": f"Best delivery week on record - {last_week} items completed",
                "severity": "ok",
            }
        elif stddev > mean:
            callouts["throughput_histogram"] = {
                "message": "Throughput is highly variable - hard to forecast reliably",
                "severity": "warn",
            }

        return callouts

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
