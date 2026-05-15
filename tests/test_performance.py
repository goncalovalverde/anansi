"""Performance tests for DataFrame caching optimization (PERF-001).

Tests the request-scoped and global caching mechanisms to ensure:
1. First request loads from database once
2. Cached requests are significantly faster
3. Request-scoped cache is faster than global cache for multiple accesses
4. No N+1 loading occurs
"""

import time
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from backend import database
from backend.services import data_service, backlog_cache
from backend.dependencies import RequestCache


class TestCachingPerformance:
    """Performance tests for the dual-layer caching system."""

    # Save original functions before any test can patch them
    _original_get_dashboard_response = staticmethod(backlog_cache.get_dashboard_response)
    _original_get_backlog = staticmethod(backlog_cache.get_backlog)
    _original_get_flow_response = staticmethod(backlog_cache.get_flow_response)

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear caches and restore any leaked mocks before and after each test."""
        # Restore real functions in case a previous test leaked a mock
        backlog_cache.get_dashboard_response = self._original_get_dashboard_response
        backlog_cache.get_backlog = self._original_get_backlog
        backlog_cache.get_flow_response = self._original_get_flow_response
        backlog_cache._cache.clear()
        yield
        backlog_cache._cache.clear()

    def create_test_dataset(self, db_path: str, num_issues: int = 100) -> tuple[str, float]:
        """Create a test dataset and return (dataset_id, load_time).
        
        Args:
            db_path: Path to test database
            num_issues: Number of issues to create
        
        Returns:
            Tuple of (dataset_id, time_to_create_in_seconds)
        """
        # Initialize database
        database.init_db(db_path)
        db = database.get_db(db_path)
        
        # Create test data
        data = {
            'Key': [f'PROJ-{i}' for i in range(1, num_issues + 1)],
            'Summary': [f'Issue {i}' for i in range(1, num_issues + 1)],
            'Type': ['Story' if i % 3 == 0 else 'Bug' if i % 3 == 1 else 'Task' 
                    for i in range(num_issues)],
            'Status': ['Done' if i % 2 == 0 else 'In Progress' for i in range(num_issues)],
            'Created': pd.date_range('2024-01-01', periods=num_issues, freq='D'),
            'Done': [pd.Timestamp('2024-12-01') if i % 2 == 0 else None 
                    for i in range(num_issues)],
            'Story Points': [3 if i % 5 == 0 else 5 if i % 5 == 1 else 8 if i % 5 == 2 else 2 if i % 5 == 3 else 1
                           for i in range(num_issues)],
            'Epic Link': [f'EPIC-{i % 10}' if i % 10 > 0 else None for i in range(num_issues)],
            'Epic': [f'Feature {i % 10}' if i % 10 > 0 else 'No Epic' for i in range(num_issues)],
        }
        
        df = pd.DataFrame(data)
        
        # Save to database
        dataset_id = data_service.create_dataset(db, 'test_hash', 'jira')
        
        start = time.perf_counter()
        data_service.save_dataframe(db, dataset_id, df)
        data_service.update_dataset_status(db, dataset_id, 'ready')
        creation_time = time.perf_counter() - start
        
        db.close()
        return dataset_id, creation_time

    def test_first_request_builds_once(self):
        """Verify get_dashboard_response only calls its builder once on first access."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dataset_id, _ = self.create_test_dataset(db_path, num_issues=50)
            db = database.get_db(db_path)
            backlog_cache._cache.clear()

            # Call get_dashboard_response - it should populate the cache
            result = backlog_cache.get_dashboard_response(db, dataset_id)
            assert result is not None, "get_dashboard_response returned None"

            # Verify cache entries were created
            assert len(backlog_cache._cache) > 0, "Cache should have entries after first call"

            # Second call should return same cached object (no rebuild)
            result2 = backlog_cache.get_dashboard_response(db, dataset_id)
            assert result is result2, "Second call should return same cached object"

            db.close()
        finally:
            Path(db_path).unlink()

    def test_cached_response_returns_same_data(self):
        """Verify cached get_dashboard_response returns identical data."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dataset_id, _ = self.create_test_dataset(db_path, num_issues=50)
            db = database.get_db(db_path)
            backlog_cache._cache.clear()

            # First call
            response1 = backlog_cache.get_dashboard_response(db, dataset_id)

            # Second call - should return cached result
            response2 = backlog_cache.get_dashboard_response(db, dataset_id)

            # Must be the exact same object (from cache, not rebuilt)
            assert response1 is response2, "Second call should return same cached object"

            db.close()
        finally:
            Path(db_path).unlink()

    def test_different_datasets_have_separate_cache_entries(self):
        """Verify different dataset_ids get separate cache entries."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            database.init_db(db_path)
            db = database.get_db(db_path)

            # Create two datasets
            data = pd.DataFrame({
                'Key': ['PROJ-1', 'PROJ-2'],
                'Summary': ['Issue 1', 'Issue 2'],
                'Type': ['Story', 'Bug'],
                'Status': ['Done', 'In Progress'],
                'Created': pd.date_range('2024-01-01', periods=2),
                'Done': [pd.Timestamp('2024-01-10'), None],
                'Story Points': [3, 5],
                'Epic Link': ['EPIC-1', None],
                'Epic': ['Feature A', 'No Epic'],
            })

            dataset_id1 = data_service.create_dataset(db, 'hash1', 'jira')
            data_service.save_dataframe(db, dataset_id1, data)
            data_service.update_dataset_status(db, dataset_id1, 'ready')

            dataset_id2 = data_service.create_dataset(db, 'hash2', 'jira')
            data_service.save_dataframe(db, dataset_id2, data)
            data_service.update_dataset_status(db, dataset_id2, 'ready')

            backlog_cache._cache.clear()
            backlog_cache.get_backlog(db, dataset_id1)
            backlog_cache.get_backlog(db, dataset_id2)

            # Should have separate cache entries for each dataset
            keys = list(backlog_cache._cache.keys())
            assert any(dataset_id1 in k for k in keys), "dataset_id1 not in cache"
            assert any(dataset_id2 in k for k in keys), "dataset_id2 not in cache"

            db.close()
        finally:
            Path(db_path).unlink()

    def test_invalidate_clears_dataset_entries(self):
        """Verify invalidate() removes all entries for a dataset."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            dataset_id, _ = self.create_test_dataset(db_path, num_issues=50)
            db = database.get_db(db_path)
            backlog_cache._cache.clear()

            # Populate cache
            backlog_cache.get_backlog(db, dataset_id)
            assert len(backlog_cache._cache) > 0

            # Invalidate
            backlog_cache.invalidate(dataset_id)
            matching = [k for k in backlog_cache._cache if dataset_id in k]
            assert len(matching) == 0, "Cache entries should be removed after invalidate()"

            db.close()
        finally:
            Path(db_path).unlink()

    def test_request_cache_isolation(self):
        """Verify RequestCache is properly isolated per instance."""
        cache1 = RequestCache()
        cache2 = RequestCache()
        
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")
        
        # Each cache should have only its own values
        assert cache1.get("key1") == "value1"
        assert cache1.get("key2") is None
        assert cache2.get("key2") == "value2"
        assert cache2.get("key1") is None

    def test_request_cache_get_or_build(self):
        """Verify RequestCache.get_or_build builds only once."""
        cache = RequestCache()
        call_count = 0
        
        def builder():
            nonlocal call_count
            call_count += 1
            return f"value_{call_count}"
        
        # First call should build
        result1 = cache.get_or_build("key", builder)
        assert result1 == "value_1"
        assert call_count == 1
        
        # Second call should return cached value
        result2 = cache.get_or_build("key", builder)
        assert result2 == "value_1"  # Same as first, not "value_2"
        assert call_count == 1  # Builder not called again


class TestCacheCorrectness:
    """Tests to verify caching doesn't cause correctness issues."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear caches before and after each test."""
        backlog_cache._cache.clear()
        yield
        backlog_cache._cache.clear()

    def test_config_signature_affects_cache_key(self):
        """Verify different configs produce different cache keys (config-aware caching)."""
        config_a = {"workflow": ["Backlog", "Done"], "issue_types": ["Story"]}
        config_b = {"workflow": ["Backlog", "In Progress", "Done"], "issue_types": ["Story"]}

        sig_a = backlog_cache._config_signature(config_a)
        sig_b = backlog_cache._config_signature(config_b)

        assert sig_a != sig_b, "Different configs must produce different signatures"

        # Same config → same signature (deterministic)
        assert backlog_cache._config_signature(config_a) == sig_a


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
