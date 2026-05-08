"""backlog_data.py — data-preparation layer for the Backlog viewer.

Responsibilities:
  - Hold the pre-computed DataFrames that all chart methods consume (BacklogData).
  - Provide pure, stateless time-series helpers used by chart methods
    (build_weekly_counts, build_event_wip, build_cumulative_series).

Nothing in this module knows about Plotly, chart configuration, or HTTP routes.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class BacklogData:
    """Immutable container for the DataFrames derived from raw cycle data.

    Constructed via ``BacklogData.from_cycle_data()`` and stored as
    ``Backlog.data``. Separates data-preparation from chart-generation so
    ``Backlog`` focuses solely on producing Plotly figures and ``BacklogData``
    can be constructed and tested independently.
    """

    treemap_data: pd.DataFrame  # all non-epic issues with cycle time appended
    done_df: pd.DataFrame       # treemap_data rows where done_step column is not null
    active_df: pd.DataFrame     # treemap_data rows where done_step column is null
    ct_df: pd.DataFrame         # done_df rows with valid positive cycle time

    @classmethod
    def from_cycle_data(cls, treemap_data: pd.DataFrame, done_step: str) -> "BacklogData":
        """Derive the four standard DataFrames from a fully-built treemap_data frame.

        Args:
            treemap_data: Filtered, cycle-time-annotated DataFrame produced by
                          ``Backlog.get_treemap_data`` + ``Backlog.calculate_cycle_time``.
            done_step: Column name that holds the done date (e.g. "Done").

        Returns:
            A ``BacklogData`` instance ready for use by chart methods.
        """
        if done_step in treemap_data.columns:
            done_mask = treemap_data[done_step].notna()
            done_df = treemap_data[done_mask].copy()
            active_df = treemap_data[~done_mask].copy()
        else:
            done_df = pd.DataFrame(columns=treemap_data.columns)
            active_df = treemap_data.copy()

        if "Cycle Time" in done_df.columns:
            ct_df = done_df[done_df["Cycle Time"].notna() & (done_df["Cycle Time"] > 0)]
        else:
            ct_df = pd.DataFrame()

        return cls(
            treemap_data=treemap_data,
            done_df=done_df,
            active_df=active_df,
            ct_df=ct_df,
        )

    @staticmethod
    def build_weekly_counts(dates: pd.Series, fill_zeros: bool = False) -> pd.Series:
        """Convert a date Series to weekly item counts.

        Args:
            dates: Series of date/datetime values. Parsing and NaT-dropping are
                   handled internally so callers skip the ``pd.to_datetime`` boilerplate.
            fill_zeros: When True, every week in the min-to-max range is present in the
                        result with 0 for empty weeks. Use for charts that must show
                        gaps explicitly (e.g. throughput histogram).

        Returns:
            Period-indexed (freq="W") Series of integer counts, sorted ascending.
            Returns an empty Series if dates is empty after parsing.
        """
        parsed = pd.to_datetime(dates, errors="coerce").dropna()
        if parsed.empty:
            return pd.Series(dtype=int)
        weekly = parsed.dt.to_period("W").value_counts().sort_index()
        if fill_zeros:
            all_weeks = pd.period_range(weekly.index.min(), weekly.index.max(), freq="W")
            weekly = weekly.reindex(all_weeks, fill_value=0)
        return weekly

    @staticmethod
    def build_event_wip(
        in_prog_dates: pd.Series,
        done_dates: Optional[pd.Series] = None,
    ) -> pd.Series:
        """Compute weekly WIP counts from entry/exit events.

        Assigns +1 to each week an item enters in-progress and -1 to each week
        it completes, then produces a running cumulative sum. O(n log n) — one
        sort + resample — versus an O(n x weeks) mask loop.

        Args:
            in_prog_dates: Series of start dates. Parsing and NaT-dropping are
                           handled internally.
            done_dates: Optional Series of completion dates. Omit or pass None
                        when no done-date column is available.

        Returns:
            DatetimeIndex-indexed (freq="W") Series of integer WIP counts, sorted
            ascending. ``clip(lower=0)`` guards against done-before-started anomalies.
            Returns an empty Series when in_prog_dates is empty after parsing.
        """
        parsed_in_prog = pd.to_datetime(in_prog_dates, errors="coerce").dropna()
        if parsed_in_prog.empty:
            return pd.Series(dtype=int)

        entries = pd.Series(1, index=pd.DatetimeIndex(parsed_in_prog.values))

        if done_dates is not None and len(done_dates) > 0:
            parsed_done = pd.to_datetime(done_dates, errors="coerce").dropna()
            exits = pd.Series(-1, index=pd.DatetimeIndex(parsed_done.values))
            events = pd.concat([entries, exits]).sort_index()
        else:
            events = entries.sort_index()

        weekly_delta = events.resample("W").sum()
        full_weeks = pd.date_range(start=events.index.min(), end=events.index.max(), freq="W")
        return weekly_delta.reindex(full_weeks, fill_value=0).cumsum().clip(lower=0).astype(int)

    @staticmethod
    def build_cumulative_series(dates: pd.Series, week_range: pd.DatetimeIndex) -> pd.Series:
        """Cumulative count of items at or before each week in week_range.

        Uses ``np.searchsorted`` on a sorted array — O(w log n) vs the previous
        O(n x w) boolean-mask approach (where w = number of weeks, n = items).

        Args:
            dates: Series of date/datetime values. Parsing and NaT-dropping are
                   handled internally.
            week_range: DatetimeIndex of weekly timestamps to evaluate at (defines
                        the shared x-axis across all series on a chart).

        Returns:
            Integer Series indexed by week_range with the running item count at
            each week-end. Returns all-zeros if dates is empty after parsing.
        """
        parsed = pd.to_datetime(dates, errors="coerce").dropna().sort_values()
        if parsed.empty:
            return pd.Series(0, index=week_range, dtype=int)
        return pd.Series(
            np.searchsorted(parsed.values, week_range.values, side="right"),
            index=week_range,
            dtype=int,
        )
