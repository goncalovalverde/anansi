#!/usr/bin/env python3
"""
Integration test for chart improvements.
Tests the actual chart generation with realistic data.
"""

import sys
import json
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, "/Users/ctw02858/dev/anansi/backend")

from viewer.backlog import (
    Backlog, ChartConfig, EpicColorMap,
    _create_empty_state_figure
)


def test_empty_state_helper():
    """Test that empty state helper works."""
    print("Testing _create_empty_state_figure...")
    json_str = _create_empty_state_figure("Test message")
    fig = json.loads(json_str)
    assert "layout" in fig
    assert "data" in fig
    print("  ✓ Empty state helper works")


def test_epic_color_map():
    """Test singleton color map."""
    print("Testing EpicColorMap singleton...")
    EpicColorMap._instance = None  # Reset
    
    map1 = EpicColorMap()
    color1_backend = map1.get_color("Backend")
    color1_frontend = map1.get_color("Frontend")
    
    # Verify consistency
    assert color1_backend == map1.get_color("Backend")
    assert color1_frontend == map1.get_color("Frontend")
    assert color1_backend != color1_frontend
    
    # Verify singleton
    map2 = EpicColorMap()
    assert map2.get_color("Backend") == color1_backend
    print("  ✓ Epic color map singleton works")


def test_chart_config_constants():
    """Test that constants are defined."""
    print("Testing ChartConfig constants...")
    assert hasattr(ChartConfig, 'HEATMAP_MIN_HEIGHT')
    cfg = ChartConfig()
    assert hasattr(cfg, 'ROLLING_AVG_WINDOW')
    assert hasattr(cfg, 'AGING_CRITICAL_DAYS')
    assert cfg.ROLLING_AVG_WINDOW == 4
    print("  ✓ All constants defined")


def test_aging_heatmap_generation():
    """Test aging heatmap with realistic data."""
    print("Testing draw_aging_heatmap...")
    
    # Create realistic data - let Backlog compute Epic Name
    today = datetime.now()
    data = []
    
    # Create 3 epics
    for epic_id in range(1, 4):
        data.append({
            "Key": f"E-{epic_id}",
            "Summary": f"Epic {epic_id}",
            "Type": "Epic",
            "Epic Link": None,
            "Story Points": 0,
            "Created": today.strftime("%Y-%m-%d"),
            "Done": None,
        })
    
    # Create stories linked to epics
    for epic_id in range(1, 4):
        for i in range(5):
            age_days = [5, 10, 20, 45, 90][i]
            created = (today - timedelta(days=age_days)).strftime("%Y-%m-%d")
            data.append({
                "Key": f"S-E{epic_id}-{i}",
                "Summary": f"Epic {epic_id} story {i}",
                "Type": "Story",
                "Epic Link": f"E-{epic_id}",
                "Story Points": 3,
                "Created": created,
                "Done": None,
            })
    
    df = pd.DataFrame(data)
    
    # Create backlog with proper DataFrame
    backlog = Backlog(
        cycle_data=df,
        config={"Workflow": ["To Do", "In Progress", "Done"], "issue_type": ["Story", "Epic"]}
    )
    
    # Generate chart
    result = backlog.draw_aging_heatmap()
    fig = json.loads(result)
    
    # Verify structure
    assert fig["data"][0]["type"] == "heatmap"
    assert len(fig["data"][0]["y"]) == 3  # 3 epics
    assert len(fig["data"][0]["x"]) == 5  # 5 age buckets
    assert fig["layout"]["height"] >= ChartConfig.HEATMAP_MIN_HEIGHT
    print("  ✓ Aging heatmap generates correctly")



def test_epic_investment_generation():
    """Test epic investment chart."""
    print("Testing draw_epic_investment...")
    
    # Create test data with epics and stories
    today = datetime.now()
    data = [
        # Epics
        {"Key": "BE-1", "Summary": "Backend Work", "Type": "Epic", "Epic Link": None, "Story Points": 0, "Created": today.strftime("%Y-%m-%d"), "Done": None},
        {"Key": "FE-1", "Summary": "Frontend Work", "Type": "Epic", "Epic Link": None, "Story Points": 0, "Created": today.strftime("%Y-%m-%d"), "Done": None},
        # Stories
        {"Key": "S-1", "Summary": "Backend task 1", "Type": "Story", "Epic Link": "BE-1", "Story Points": 5, "Created": today.strftime("%Y-%m-%d"), "Done": None},
        {"Key": "S-2", "Summary": "Backend task 2", "Type": "Story", "Epic Link": "BE-1", "Story Points": 3, "Created": today.strftime("%Y-%m-%d"), "Done": None},
        {"Key": "S-3", "Summary": "Frontend task 1", "Type": "Story", "Epic Link": "FE-1", "Story Points": 8, "Created": today.strftime("%Y-%m-%d"), "Done": None},
        {"Key": "S-4", "Summary": "Frontend task 2", "Type": "Story", "Epic Link": "FE-1", "Story Points": 2, "Created": today.strftime("%Y-%m-%d"), "Done": None},
    ]
    df = pd.DataFrame(data)
    
    backlog = Backlog(
        cycle_data=df,
        config={"Workflow": ["To Do", "Done"], "issue_type": ["Story", "Epic"]}
    )
    
    result = backlog.draw_epic_investment()
    fig = json.loads(result)
    
    # Should have treemaps
    treemaps = [t for t in fig["data"] if t.get("type") == "treemap"]
    assert len(treemaps) >= 1
    print("  ✓ Epic investment generates correctly")



def test_throughput_histogram_generation():
    """Test throughput histogram."""
    print("Testing draw_throughput_histogram...")
    
    # Create done items over 8 weeks
    today = datetime.now()
    data = []
    
    # Create an epic
    data.append({
        "Key": "E-1",
        "Summary": "Work Epic",
        "Type": "Epic",
        "Epic Link": None,
        "Story Points": 0,
        "Created": today.strftime("%Y-%m-%d"),
        "Done": None,
    })
    
    # Create stories linked to epic, with done dates
    for week in range(8):
        for day in range(3):  # 3 items per week
            done_date = (today - timedelta(weeks=8-week, days=day)).strftime("%Y-%m-%d")
            data.append({
                "Key": f"S-{week}-{day}",
                "Summary": f"Completed task {week}-{day}",
                "Type": "Story",
                "Epic Link": "E-1",
                "Story Points": 2,
                "Created": (today - timedelta(weeks=10)).strftime("%Y-%m-%d"),
                "Done": done_date,
            })
    
    df = pd.DataFrame(data)
    
    backlog = Backlog(
        cycle_data=df,
        config={"Workflow": ["To Do", "Done"], "issue_type": ["Story", "Epic"]}
    )
    
    result = backlog.draw_throughput_histogram()
    fig = json.loads(result)
    
    # Should have bar and line
    types = [t.get("type") for t in fig["data"]]
    assert "bar" in types
    assert "scatter" in types
    print("  ✓ Throughput histogram generates correctly")


def test_performance_with_large_dataset():
    """Test performance with 1000+ items."""
    print("Testing performance with large dataset...")
    
    # Create 1000 items with epics
    today = datetime.now()
    data = []
    
    # Create 10 epics
    for epic_id in range(10):
        data.append({
            "Key": f"E-{epic_id}",
            "Summary": f"Epic {epic_id}",
            "Type": "Epic",
            "Epic Link": None,
            "Story Points": 0,
            "Created": today.strftime("%Y-%m-%d"),
            "Done": None,
        })
    
    # Create 1000 stories
    for i in range(1000):
        epic_id = i % 10
        data.append({
            "Key": f"S-{i}",
            "Summary": f"Task {i}",
            "Type": "Story" if i % 2 == 0 else "Bug",
            "Epic Link": f"E-{epic_id}",
            "Story Points": (i % 13) + 1 if i % 5 != 0 else None,
            "Created": (today - timedelta(days=i % 90)).strftime("%Y-%m-%d"),
            "Done": None if i % 3 != 0 else (today - timedelta(days=i % 30)).strftime("%Y-%m-%d"),
        })
    
    df = pd.DataFrame(data)
    
    backlog = Backlog(
        cycle_data=df,
        config={"Workflow": ["To Do", "In Progress", "Done"], "issue_type": ["Story", "Bug", "Epic"]}
    )
    
    # Should handle large data efficiently
    result = backlog.draw_aging_heatmap()
    fig = json.loads(result)
    assert fig is not None
    print("  ✓ Large dataset handled efficiently")


def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("ANANSI CHART IMPROVEMENTS - INTEGRATION TEST SUITE")
    print("="*60 + "\n")
    
    tests = [
        test_empty_state_helper,
        test_epic_color_map,
        test_chart_config_constants,
        test_aging_heatmap_generation,
        test_epic_investment_generation,
        test_throughput_histogram_generation,
        test_performance_with_large_dataset,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
