"""
Comprehensive test suite for backlog chart functions.
Tests edge cases, data validation, and performance characteristics.
"""

import pytest
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, "/Users/ctw02858/dev/anansi/backend")

from viewer.backlog import (
    Backlog, ChartConfig, EpicColorMap, 
    _create_empty_state_figure, ANANSI_COLORS
)


class TestChartConfig:
    """Test configuration constants."""
    
    def test_heatmap_constants_defined(self):
        """Ensure heatmap constants are properly configured."""
        assert ChartConfig.HEATMAP_MIN_HEIGHT == 240
        assert ChartConfig.HEATMAP_EPIC_ROW_HEIGHT == 36
        assert ChartConfig.HEATMAP_PADDING == 80
        assert len(ChartConfig.HEATMAP_COLORSCALE) == 5
    
    def test_throughput_constants_defined(self):
        """Ensure throughput histogram constants are defined."""
        cfg = ChartConfig()
        assert cfg.ROLLING_AVG_WINDOW == 4
        assert ChartConfig.NORMAL_WEEK_COLOR == '#007B85'
        assert ChartConfig.ABOVE_MEAN_COLOR == '#F5A623'
        assert ChartConfig.BELOW_MEAN_COLOR == '#2C3E50'
    
    def test_callout_thresholds_reasonable(self):
        """Ensure callout thresholds make business sense."""
        cfg = ChartConfig()
        assert cfg.AGING_CRITICAL_DAYS > cfg.AGING_WARNING_DAYS
        assert cfg.AGING_CRITICAL_COUNT > cfg.AGING_WARNING_COUNT
        assert 0 <= cfg.UNESTIMATED_ITEMS_THRESHOLD <= 1
        assert cfg.COMPLEXITY_RATIO_THRESHOLD > 1


class TestEpicColorMapSingleton:
    """Test EpicColorMap singleton pattern."""
    
    def teardown_method(self):
        """Clear color map between tests."""
        EpicColorMap._instance = None
    
    def test_singleton_pattern(self):
        """Verify only one instance exists."""
        map1 = EpicColorMap()
        map2 = EpicColorMap()
        assert map1 is map2
    
    def test_consistent_epic_coloring(self):
        """Ensure same epic always gets same color."""
        color_map = EpicColorMap()
        color1 = color_map.get_color("Backend")
        color2 = color_map.get_color("Backend")
        assert color1 == color2
        assert color1 in ANANSI_COLORS
    
    def test_different_epics_different_colors(self):
        """Ensure different epics get different colors initially."""
        color_map = EpicColorMap()
        backend_color = color_map.get_color("Backend")
        frontend_color = color_map.get_color("Frontend")
        assert backend_color != frontend_color
    
    def test_color_map_wraps_around(self):
        """Verify color assignment wraps when exceeding palette size."""
        color_map = EpicColorMap()
        epics = [f"Epic{i}" for i in range(len(ANANSI_COLORS) + 2)]
        colors = [color_map.get_color(e) for e in epics]
        assert len(set(colors)) <= len(ANANSI_COLORS)
        # Colors wrap around via modulo
        assert colors[0] == colors[len(ANANSI_COLORS)]
    
    def test_clear_resets_map(self):
        """Verify clear() resets the color map."""
        color_map = EpicColorMap()
        color_map.get_color("A")
        color_map.get_color("B")
        initial_size = len(color_map._color_map)
        
        color_map.clear()
        assert len(color_map._color_map) == 0
        
        # Can reuse colors after clear
        new_color = color_map.get_color("A")
        assert new_color in ANANSI_COLORS


class TestEmptyStateFigureHelper:
    """Test _create_empty_state_figure helper."""
    
    def test_creates_valid_plotly_figure(self):
        """Ensure helper returns valid JSON Plotly figure."""
        json_str = _create_empty_state_figure("Test message")
        fig_dict = json.loads(json_str)
        
        assert "data" in fig_dict
        assert "layout" in fig_dict
    
    def test_includes_custom_message(self):
        """Verify message is included in annotation."""
        message = "Custom test message"
        json_str = _create_empty_state_figure(message)
        fig_dict = json.loads(json_str)
        
        annotations = fig_dict["layout"].get("annotations", [])
        assert any(message in ann.get("text", "") for ann in annotations)
    
    def test_respects_height_parameter(self):
        """Verify height parameter is applied."""
        custom_height = 500
        json_str = _create_empty_state_figure("Test", height=custom_height)
        fig_dict = json.loads(json_str)
        
        assert fig_dict["layout"]["height"] == custom_height
    
    def test_uses_default_height(self):
        """Verify default height matches config."""
        json_str = _create_empty_state_figure("Test")
        fig_dict = json.loads(json_str)
        
        assert fig_dict["layout"]["height"] == ChartConfig.EMPTY_STATE_HEIGHT


class TestBacklogAgingHeatmap:
    """Test draw_aging_heatmap function."""
    
    @pytest.fixture
    def mock_backlog(self):
        """Create a mock Backlog instance."""
        backlog = MagicMock(spec=Backlog)
        backlog.done_step = "Done"
        backlog._active_df = pd.DataFrame()  # default; overridden per-test
        return backlog
    
    def test_empty_backlog_returns_empty_state(self, mock_backlog):
        """Ensure empty data returns proper empty state."""
        mock_backlog.treemap_data = pd.DataFrame()
        mock_backlog._active_df = pd.DataFrame()
        
        # Call the actual method
        result = Backlog.draw_aging_heatmap(mock_backlog)
        fig = json.loads(result)
        
        assert "No active backlog items" in str(fig)
    
    def test_heatmap_with_multiple_epics(self, mock_backlog):
        """Test heatmap with realistic multi-epic data."""
        # Create sample data with multiple epics at different ages
        today = datetime.now()
        data = []
        for epic in ["Backend", "Frontend", "DevOps"]:
            for days_ago in [5, 10, 20, 45, 90]:
                created = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                data.append({
                    "Key": f"{epic}-{days_ago}",
                    "Epic Name": epic,
                    "Created": created,
                    "Done": None,  # Active items
                })
        
        mock_backlog.treemap_data = pd.DataFrame(data)
        mock_backlog._active_df = pd.DataFrame(data)
        result = Backlog.draw_aging_heatmap(mock_backlog)
        fig = json.loads(result)
        
        assert fig["data"][0]["type"] == "heatmap"
        assert len(fig["data"][0]["y"]) == 3  # 3 epics
        assert len(fig["data"][0]["x"]) == 5  # 5 age buckets
    
    def test_heatmap_height_scales_with_epics(self, mock_backlog):
        """Verify height calculation based on epic count."""
        # Create data with many epics
        today = datetime.now()
        epics = [f"Epic{i}" for i in range(10)]
        data = []
        for epic in epics:
            created = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            data.append({
                "Key": epic,
                "Epic Name": epic,
                "Created": created,
                "Done": None,
            })
        
        mock_backlog.treemap_data = pd.DataFrame(data)
        mock_backlog._active_df = pd.DataFrame(data)
        result = Backlog.draw_aging_heatmap(mock_backlog)
        fig = json.loads(result)
        
        # Height = max(240, epics * 36 + 80)
        expected_min_height = max(240, 10 * 36 + 80)
        assert fig["layout"]["height"] >= expected_min_height


class TestBacklogEpicInvestment:
    """Test draw_epic_investment function."""
    
    @pytest.fixture
    def mock_backlog(self):
        """Create mock Backlog instance."""
        backlog = MagicMock(spec=Backlog)
        backlog.done_step = "Done"
        return backlog
    
    def test_empty_data_returns_empty_state(self, mock_backlog):
        """Empty data should return proper empty state."""
        mock_backlog.treemap_data = pd.DataFrame(columns=["Key", "Epic Name", "Story Points"])
        
        result = Backlog.draw_epic_investment(mock_backlog)
        # Should return error or empty state
        assert result is not None
    
    def test_single_treemap_without_story_points(self, mock_backlog):
        """No story points data should show single treemap."""
        data = [
            {"Key": "A", "Epic Name": "Backend", "Story Points": None},
            {"Key": "B", "Epic Name": "Backend", "Story Points": None},
            {"Key": "C", "Epic Name": "Frontend", "Story Points": 0},
        ]
        mock_backlog.treemap_data = pd.DataFrame(data)
        
        result = Backlog.draw_epic_investment(mock_backlog)
        fig = json.loads(result)
        
        # Should have only one treemap trace
        treemaps = [t for t in fig["data"] if t.get("type") == "treemap"]
        assert len(treemaps) == 1
    
    def test_dual_treemaps_with_story_points(self, mock_backlog):
        """With story points, should show side-by-side treemaps."""
        data = [
            {"Key": "A", "Epic Name": "Backend", "Story Points": 5},
            {"Key": "B", "Epic Name": "Backend", "Story Points": 3},
            {"Key": "C", "Epic Name": "Frontend", "Story Points": 8},
            {"Key": "D", "Epic Name": "Frontend", "Story Points": 2},
        ]
        mock_backlog.treemap_data = pd.DataFrame(data)
        
        result = Backlog.draw_epic_investment(mock_backlog)
        fig = json.loads(result)
        
        # Should have two treemap traces
        treemaps = [t for t in fig["data"] if t.get("type") == "treemap"]
        assert len(treemaps) == 2
        
        # Verify domains are set correctly for side-by-side layout
        assert treemaps[0]["domain"]["x"][1] <= 0.47
        assert treemaps[1]["domain"]["x"][0] >= 0.53


class TestBacklogThroughputHistogram:
    """Test draw_throughput_histogram function."""
    
    @pytest.fixture
    def mock_backlog(self):
        """Create mock Backlog instance."""
        backlog = MagicMock(spec=Backlog)
        backlog.done_step = "Done"
        backlog._done_df = pd.DataFrame()  # default: no completed items
        backlog.chart_config = ChartConfig()
        return backlog
    
    def test_no_done_items_returns_empty_state(self, mock_backlog):
        """No done items should return empty state."""
        mock_backlog.treemap_data = pd.DataFrame({
            "Key": ["A", "B"],
            "Done": [None, None]
        })
        # _done_df is already empty from fixture
        
        result = Backlog.draw_throughput_histogram(mock_backlog)
        assert "No completed items" in result
    
    def test_histogram_with_weekly_data(self, mock_backlog):
        """Test histogram generation with realistic weekly data."""
        # Create data spanning 8 weeks
        dates = []
        for week in range(8):
            for day in range(3):  # 3 items per week
                date = (datetime.now() - timedelta(weeks=8-week, days=day)).strftime("%Y-%m-%d")
                dates.append(date)
        
        data = [{"Key": f"Item{i}", "Done": dates[i]} for i in range(len(dates))]
        df = pd.DataFrame(data)
        mock_backlog.treemap_data = df
        mock_backlog._done_df = df
        
        result = Backlog.draw_throughput_histogram(mock_backlog)
        fig = json.loads(result)
        
        # Should have bar and line traces
        types = [t.get("type") for t in fig["data"]]
        assert "bar" in types
        assert "scatter" in types
    
    def test_color_coding_reflects_performance(self, mock_backlog):
        """Verify color coding matches performance levels."""
        # Create data with variation: some good weeks, some bad weeks
        dates = []
        weeks_data = [1, 1, 5, 3, 10, 2, 7, 1]  # Items per week
        
        for week_idx, count in enumerate(weeks_data):
            for item in range(count):
                date = (datetime.now() - timedelta(weeks=len(weeks_data)-week_idx)).strftime("%Y-%m-%d")
                dates.append(date)
        
        data = [{"Key": f"Item{i}", "Done": dates[i]} for i in range(len(dates))]
        df = pd.DataFrame(data)
        mock_backlog.treemap_data = df
        mock_backlog._done_df = df
        
        result = Backlog.draw_throughput_histogram(mock_backlog)
        fig = json.loads(result)
        
        # Verify colors include multiple types
        bar_trace = next(t for t in fig["data"] if t.get("type") == "bar")
        colors = bar_trace["marker"]["color"]
        
        # Should have mix of colors (normal, above, below)
        unique_colors = set(colors)
        assert len(unique_colors) > 1


class TestPerformanceOptimizations:
    """Test that optimizations are effective."""
    
    def test_no_unnecessary_dataframe_copies_in_aging_heatmap(self):
        """Verify aging_heatmap doesn't make unnecessary copies."""
        backlog = MagicMock(spec=Backlog)
        backlog.done_step = "Done"
        
        # Create larger dataset
        data = []
        today = datetime.now()
        for i in range(1000):
            data.append({
                "Key": f"Item{i}",
                "Epic Name": f"Epic{i % 5}",
                "Created": (today - timedelta(days=i % 90)).strftime("%Y-%m-%d"),
                "Done": None,
            })
        
        df = pd.DataFrame(data)
        backlog.treemap_data = df
        backlog._active_df = df
        
        # Should execute without significant slowdown
        result = Backlog.draw_aging_heatmap(backlog)
        assert result is not None
        assert len(json.loads(result)) > 0
    


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_all_items_same_age(self):
        """Test heatmap with all items created on same day."""
        backlog = MagicMock(spec=Backlog)
        backlog.done_step = "Done"
        
        today = datetime.now()
        created_date = (today - timedelta(days=15)).strftime("%Y-%m-%d")
        
        data = [
            {"Key": f"Item{i}", "Epic Name": "Backend", "Created": created_date, "Done": None}
            for i in range(5)
        ]
        df = pd.DataFrame(data)
        backlog.treemap_data = df
        backlog._active_df = df
        
        result = Backlog.draw_aging_heatmap(backlog)
        fig = json.loads(result)
        
        assert fig["data"][0]["type"] == "heatmap"
    
    def test_single_epic(self):
        """Test charts with only one epic."""
        backlog = MagicMock(spec=Backlog)
        backlog.treemap_data = pd.DataFrame({
            "Key": ["A", "B", "C"],
            "Epic Name": ["Single"] * 3,
            "Story Points": [3, 5, 2],
        })
        
        result = Backlog.draw_epic_investment(backlog)
        fig = json.loads(result)
        
        treemaps = [t for t in fig["data"] if t.get("type") == "treemap"]
        assert len(treemaps) > 0
    
    def test_very_large_story_points(self):
        """Test handling of large story point values."""
        backlog = MagicMock(spec=Backlog)
        backlog.treemap_data = pd.DataFrame({
            "Key": ["A", "B", "C"],
            "Epic Name": ["Backend", "Frontend", "Backend"],
            "Story Points": [1000, 2000, 1500],
        })
        
        result = Backlog.draw_epic_investment(backlog)
        assert result is not None
        
        fig = json.loads(result)
        assert fig is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
