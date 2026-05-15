"""Insights and callouts generation for backlog analysis.

Extracted from Backlog to separate delivery-health intelligence
from chart rendering. This module contains no Plotly dependency.
"""

from datetime import datetime

import numpy as np
import pandas as pd


class BacklogInsightsMixin:
    """Mixin providing insight and callout methods for the Backlog class.

    Expects the host class to provide:
      - self.treemap_data: pd.DataFrame
      - self._done_df, self._active_df, self._ct_df: pre-computed DataFrames
      - self.in_progress_step, self.done_step: str
      - self.chart_config: ChartConfig instance
      - self.config: dict
    """

    def get_insights(self) -> list:
        df = self.treemap_data
        in_prog_col = self.in_progress_step
        cfg = self.chart_config
        insights = []

        # 1. Completed count check
        done_count = len(self._done_df)
        if done_count == 0:
            insights.append({"type": "alert", "message": "No items marked Done - delivery may be stalled"})
        else:
            insights.append({"type": "ok", "message": f"{done_count} items completed this period"})

        # 2. WIP check
        in_prog = int(df[in_prog_col].notna().sum()) if in_prog_col in df.columns else 0
        if in_prog > cfg.WIP_HIGH_THRESHOLD:
            insights.append({"type": "alert", "message": f"High WIP - {in_prog} items active simultaneously"})
        elif in_prog > cfg.WIP_ELEVATED_THRESHOLD:
            insights.append(
                {"type": "warn", "message": f"WIP is elevated ({in_prog} items) - consider limiting parallel work"}
            )

        # 3. Cycle time check
        if not self._ct_df.empty:
            avg = round(float(self._ct_df["Cycle Time"].mean()), 1)
            if avg > cfg.CYCLE_TIME_HIGH_DAYS:
                insights.append(
                    {
                        "type": "warn",
                        "message": f"Average cycle time is {avg} days - items are taking over a month to complete",
                    }
                )
            elif avg <= cfg.CYCLE_TIME_HEALTHY_DAYS:
                insights.append({"type": "ok", "message": f"Cycle time is healthy at {avg} days on average"})

        # 4. Bug ratio check
        if "Type" in df.columns:
            total = len(df)
            bugs = df["Type"].str.lower().isin({"bug", "defect"}).sum()
            if total > 0:
                ratio = round(bugs / total * 100, 1)
                if ratio > cfg.BUG_RATIO_HIGH_PCT:
                    insights.append(
                        {
                            "type": "alert",
                            "message": f"Bug ratio is {ratio}% - quality issues may be affecting delivery",
                        }
                    )
                elif ratio > cfg.BUG_RATIO_ELEVATED_PCT:
                    insights.append({"type": "warn", "message": f"Bug ratio is {ratio}% - worth monitoring"})

        # 5. Backlog growth
        if "Created" in df.columns:
            created = df["Created"].dropna()
            if len(created) > 0:
                mid = created.median()
                first_half = (created <= mid).sum()
                second_half = (created > mid).sum()
                if first_half > 0 and second_half > first_half * cfg.BACKLOG_GROWTH_RATIO:
                    pct = round((second_half - first_half) / first_half * 100)
                    insights.append(
                        {
                            "type": "warn",
                            "message": f"Backlog grew {pct}% this period - more is being added than completed",
                        }
                    )
                elif second_half < first_half:
                    insights.append({"type": "ok", "message": "Backlog is shrinking - good sign of delivery focus"})

        # Sort: alert first, then warn, then ok; cap at 5
        order = {"alert": 0, "warn": 1, "ok": 2}
        insights.sort(key=lambda x: order.get(x["type"], 3))
        return insights[:5]

    def get_callouts(self) -> dict:
        df = self.treemap_data
        cfg = self.chart_config
        callouts = {}
        done_data = self._done_df
        active_df = self._active_df
        ct_df = self._ct_df

        # treemap
        if done_data.empty:
            callouts["treemap"] = {
                "message": "No completed work to display - items may not be reaching Done status",
                "severity": "alert",
            }
        else:
            n_epics = done_data["Epic Name"].nunique()
            if n_epics == 1:
                callouts["treemap"] = {
                    "message": "Only 1 epic has completed items - are other epics blocked or not yet started?",
                    "severity": "warn",
                }

        # pbis_done
        if done_data.empty:
            callouts["pbis_done"] = {"message": "No items completed in this period", "severity": "alert"}

        # story_points
        sp_col = "Story Points"
        if sp_col not in df.columns or pd.to_numeric(df[sp_col], errors="coerce").fillna(0).sum() == 0:
            callouts["story_points"] = {
                "message": "No story points recorded - check that story point field ID is configured correctly",
                "severity": "warn",
            }
        else:
            by_epic = df.groupby("Epic Name")[sp_col].apply(lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum())
            total_sp = by_epic.sum()
            if total_sp > 0:
                top_pct = by_epic.max() / total_sp
                if top_pct > cfg.CALLOUT_EPIC_CONCENTRATION_PCT:
                    callouts["story_points"] = {
                        "message": "One epic is consuming most delivery capacity - other areas may be under-resourced",
                        "severity": "warn",
                    }

        # type_issue - bug ratio
        if "Type" in df.columns:
            total = len(df)
            bug_types = {"bug", "defect"}
            bugs = df["Type"].str.lower().isin(bug_types).sum()
            if total > 0:
                ratio = round(bugs / total * 100, 1)
                if ratio > cfg.CALLOUT_BUG_RATIO_HIGH_PCT:
                    callouts["type_issue"] = {
                        "message": f"High defect ratio ({ratio}%) - more than 1 in 4 items is a bug or defect",
                        "severity": "alert",
                    }
                elif bugs == 0:
                    callouts["type_issue"] = {"message": "No bugs or defects in this period", "severity": "ok"}

        # timeline - use pre-computed ct_df
        if not ct_df.empty:
            avg_ct = ct_df["Cycle Time"].mean()
            max_row = ct_df.loc[ct_df["Cycle Time"].idxmax()]
            max_ct = int(max_row["Cycle Time"])
            if max_ct > cfg.CALLOUT_CYCLE_TIME_ALERT_DAYS:
                name = str(max_row.get("Summary", "An item"))[:50]
                callouts["timeline_size"] = {
                    "message": f"{name} has been in progress for {max_ct} days",
                    "severity": "alert",
                }
            elif avg_ct > cfg.CALLOUT_CYCLE_TIME_WARN_DAYS:
                callouts["timeline_size"] = {
                    "message": f"Average item age is {round(avg_ct)} days - consider breaking work into smaller pieces",
                    "severity": "warn",
                }
            else:
                outliers = (ct_df["Cycle Time"] > cfg.CALLOUT_OUTLIER_CT_MULTIPLIER * avg_ct).sum()
                if outliers > 0:
                    label = "items" if outliers > 1 else "item"
                    callouts["timeline_size"] = {
                        "message": (
                            f"{outliers} {label} took more than"
                            f" {cfg.CALLOUT_OUTLIER_CT_MULTIPLIER}x the average to complete"
                        ),
                        "severity": "warn",
                    }

        # aging_heatmap - use pre-computed active_df
        if not active_df.empty and "Created" in active_df.columns:
            today = pd.Timestamp(datetime.now().date())
            created = pd.to_datetime(active_df["Created"], errors="coerce")
            age_days = (today - created).dt.days.fillna(0)

            old_counts = active_df[age_days >= cfg.AGING_CRITICAL_DAYS].groupby("Epic Name").size()
            if not old_counts.empty:
                worst_epic = old_counts.idxmax()
                worst_count = int(old_counts[worst_epic])
                if worst_count > cfg.AGING_CRITICAL_COUNT:
                    callouts["aging_heatmap"] = {
                        "message": (
                            f"{worst_epic} has {worst_count} items older than"
                            f" {cfg.AGING_CRITICAL_DAYS} days - these may be blocked or forgotten"
                        ),
                        "severity": "alert",
                    }
                else:
                    month_mask = (age_days >= cfg.AGING_WARNING_DAYS) & (age_days < cfg.AGING_CRITICAL_DAYS)
                    month_total = int(month_mask.sum())
                    if month_total > cfg.AGING_WARNING_COUNT:
                        callouts["aging_heatmap"] = {
                            "message": (
                                f"{month_total} items are between"
                                f" {cfg.AGING_WARNING_DAYS}-{cfg.AGING_CRITICAL_DAYS} days old"
                                " - review before they become critical"
                            ),
                            "severity": "warn",
                        }
                    else:
                        callouts["aging_heatmap"] = {
                            "message": "Backlog age is healthy - no major stale item clusters detected",
                            "severity": "ok",
                        }

        # epic_investment
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
        epic_groups = epic_groups[epic_groups["ItemCount"] > 0]

        if not epic_groups.empty:
            has_story_points = epic_groups["StoryPoints"].sum() > 0
            if not has_story_points:
                callouts["epic_investment"] = {
                    "message": (
                        "Story points not configured - add your Story Points"
                        " Field ID in Configuration to unlock this view"
                    ),
                    "severity": "warn",
                }
            else:
                epic_groups["complexity"] = epic_groups["StoryPoints"] / epic_groups["ItemCount"]
                high_complexity = epic_groups.loc[epic_groups["complexity"].idxmax()]
                low_complexity = epic_groups.loc[epic_groups["complexity"].idxmin()]
                complexity_ratio = (
                    high_complexity["complexity"] / low_complexity["complexity"]
                    if low_complexity["complexity"] > 0
                    else 0
                )
                if complexity_ratio > cfg.COMPLEXITY_RATIO_THRESHOLD:
                    high_name = high_complexity["Epic"]
                    low_name = low_complexity["Epic"]
                    high_avg = round(high_complexity["complexity"], 1)
                    low_avg = round(low_complexity["complexity"], 1)
                    callouts["epic_investment"] = {
                        "message": (
                            f"{high_name} items average {high_avg} points each vs"
                            f" {low_avg} for {low_name} - large complexity gap between epics"
                        ),
                        "severity": "warn",
                    }

        return callouts

    def get_flow_callouts(self) -> dict:
        """Callouts for Flow tab charts (throughput histogram)."""
        callouts = {}

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
