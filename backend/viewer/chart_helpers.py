"""chart_helpers.py — shared Plotly utility functions for the Backlog viewer.

Responsibilities:
  - Reusable Plotly figure builders used by multiple chart methods.

Depends on: plotly, viewer.chart_config. Does not import pandas or backlog logic.
"""

import json

import plotly.graph_objects as go

from .chart_config import ChartConfig


def _fig_to_dict(fig) -> dict:
    """Convert a Plotly figure to a JSON-safe dict without an intermediate string round-trip."""
    return json.loads(fig.to_json())


def create_empty_state_figure(message: str, height: int = ChartConfig.EMPTY_STATE_HEIGHT) -> dict:
    """Create a standardized empty state figure with a centered message.

    Used by chart methods when there is no data to display, so every empty
    state looks consistent across the dashboard.

    Args:
        message: Text to display in the center of the figure.
        height: Figure height in pixels.

    Returns:
        Dict representation of a Plotly figure ready for ``Plotly.react``.
    """
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(
            size=ChartConfig.EMPTY_STATE_FONT_SIZE,
            color=ChartConfig.EMPTY_STATE_FONT_COLOR,
        ),
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=height,
    )
    return _fig_to_dict(fig)


# Private alias keeps existing internal call sites in backlog.py working without
# touching every chart method. New code should call create_empty_state_figure directly.
_create_empty_state_figure = create_empty_state_figure
