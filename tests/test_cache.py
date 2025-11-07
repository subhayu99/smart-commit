"""Tests for commit message cache functionality."""

import pytest
import time
import json
from pathlib import Path
from smart_commit.cache import CommitMessageCache


class TestCommitMessageCache:
    """Test commit message cache functionality."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create a temporary cache directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a cache instance with temporary directory."""
        return CommitMessageCache(cache_dir=temp_cache_dir)

    def test_cache_initialization(self, temp_cache_dir):
        """Test cache initialization."""
        cache = CommitMessageCache(cache_dir=temp_cache_dir)

        assert cache.cache_dir == temp_cache_dir
        assert cache.cache_dir.exists()
        assert cache.expiry_time == 24 * 60 * 60  # 24 hours

    def test_cache_initialization_default_dir(self):
        """Test cache initialization with default directory."""
        cache = CommitMessageCache()

        expected_dir = Path.home() / ".cache" / "smart-commit"
        assert cache.cache_dir == expected_dir

    def test_set_and_get_cache(self, cache):
        """Test setting and getting cached messages."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"
        message = "feat: add hello world\n\nImplemented greeting functionality."

        # Set cache
        cache.set(diff_content, model, message)

        # Get cache
        cached_message = cache.get(diff_content, model)

        assert cached_message == message

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"

        cached_message = cache.get(diff_content, model)

        assert cached_message is None

    def test_cache_key_generation(self, cache):
        """Test that cache keys are generated correctly."""
        diff1 = "diff --git a/test.py b/test.py\n+print('hello')"
        diff2 = "diff --git a/test.py b/test.py\n+print('world')"
        model = "openai/gpt-4o"

        # Different diffs should generate different keys
        key1 = cache._get_cache_key(diff1, model)
        key2 = cache._get_cache_key(diff2, model)

        assert key1 != key2
        assert len(key1) == 64  # SHA256 hash length
        assert len(key2) == 64

    def test_cache_key_includes_model(self, cache):
        """Test that cache keys include model information."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"
        model1 = "openai/gpt-4o"
        model2 = "anthropic/claude-3-sonnet"

        # Same diff, different models should generate different keys
        key1 = cache._get_cache_key(diff, model1)
        key2 = cache._get_cache_key(diff, model2)

        assert key1 != key2

    def test_cache_expiry(self, cache):
        """Test that expired cache entries are removed."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"
        message = "feat: add hello world"

        # Set cache with expired timestamp
        cache_key = cache._get_cache_key(diff_content, model)
        cache_path = cache._get_cache_path(cache_key)

        cache_data = {
            'message': message,
            'model': model,
            'timestamp': time.time() - (25 * 60 * 60),  # 25 hours ago (expired)
        }

        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Try to get expired cache
        cached_message = cache.get(diff_content, model)

        assert cached_message is None
        assert not cache_path.exists()  # Should be deleted

    def test_cache_not_expired(self, cache):
        """Test that non-expired cache is returned."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"
        message = "feat: add hello world"

        # Set cache
        cache.set(diff_content, model, message)

        # Get cache immediately (not expired)
        cached_message = cache.get(diff_content, model)

        assert cached_message == message

    def test_cache_clear(self, cache):
        """Test clearing all cache."""
        # Add multiple cache entries
        for i in range(5):
            diff = f"diff --git a/test{i}.py b/test{i}.py\n+print('{i}')"
            cache.set(diff, "openai/gpt-4o", f"feat: add feature {i}")

        # Verify cache files exist
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 5

        # Clear cache
        count = cache.clear()

        assert count == 5
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 0

    def test_cache_clear_empty(self, cache):
        """Test clearing empty cache."""
        count = cache.clear()

        assert count == 0

    def test_cache_clear_expired(self, cache):
        """Test clearing only expired entries."""
        diff1 = "diff --git a/test1.py b/test1.py\n+print('1')"
        diff2 = "diff --git a/test2.py b/test2.py\n+print('2')"
        diff3 = "diff --git a/test3.py b/test3.py\n+print('3')"
        model = "openai/gpt-4o"

        # Add fresh cache
        cache.set(diff1, model, "feat: add feature 1")

        # Add expired cache entries manually
        for diff, msg in [(diff2, "feat: add feature 2"), (diff3, "feat: add feature 3")]:
            cache_key = cache._get_cache_key(diff, model)
            cache_path = cache._get_cache_path(cache_key)

            cache_data = {
                'message': msg,
                'model': model,
                'timestamp': time.time() - (25 * 60 * 60),  # Expired
            }

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

        # Clear expired only
        count = cache.clear_expired()

        assert count == 2  # Only expired entries
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 1  # Fresh entry remains

    def test_get_stats_empty(self, cache):
        """Test getting stats for empty cache."""
        stats = cache.get_stats()

        assert stats['total_entries'] == 0
        assert stats['cache_size_bytes'] == 0
        assert stats['cache_size_mb'] == 0
        assert str(cache.cache_dir) in stats['cache_dir']

    def test_get_stats_with_entries(self, cache):
        """Test getting stats with cache entries."""
        # Add some cache entries
        for i in range(3):
            diff = f"diff --git a/test{i}.py b/test{i}.py\n+print('{i}')"
            cache.set(diff, "openai/gpt-4o", f"feat: add feature {i}")

        stats = cache.get_stats()

        assert stats['total_entries'] == 3
        assert stats['cache_size_bytes'] > 0
        assert stats['cache_size_mb'] >= 0
        assert 'cache_dir' in stats

    def test_invalid_cache_file_handling(self, cache):
        """Test handling of invalid cache files."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"

        # Create invalid cache file
        cache_key = cache._get_cache_key(diff_content, model)
        cache_path = cache._get_cache_path(cache_key)

        with open(cache_path, 'w') as f:
            f.write("invalid json content")

        # Try to get cache (should handle gracefully)
        cached_message = cache.get(diff_content, model)

        assert cached_message is None
        assert not cache_path.exists()  # Should be deleted

    def test_cache_file_missing_fields(self, cache):
        """Test handling of cache files with missing fields."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"

        # Create cache file with missing 'message' field
        cache_key = cache._get_cache_key(diff_content, model)
        cache_path = cache._get_cache_path(cache_key)

        cache_data = {
            'model': model,
            'timestamp': time.time(),
            # Missing 'message' field
        }

        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Try to get cache
        cached_message = cache.get(diff_content, model)

        assert cached_message is None

    def test_cache_write_failure_silent(self, cache, monkeypatch):
        """Test that cache write failures are silent."""
        diff_content = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"
        message = "feat: add hello world"

        # Mock open to raise exception
        original_open = open

        def mock_open(*args, **kwargs):
            if 'w' in args or kwargs.get('mode') == 'w':
                raise IOError("Mock write error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr('builtins.open', mock_open)

        # Should not raise exception
        cache.set(diff_content, model, message)

    def test_different_diffs_different_cache(self, cache):
        """Test that different diffs have separate cache entries."""
        diff1 = "diff --git a/test1.py b/test1.py\n+print('1')"
        diff2 = "diff --git a/test2.py b/test2.py\n+print('2')"
        model = "openai/gpt-4o"

        cache.set(diff1, model, "feat: add feature 1")
        cache.set(diff2, model, "feat: add feature 2")

        cached1 = cache.get(diff1, model)
        cached2 = cache.get(diff2, model)

        assert cached1 == "feat: add feature 1"
        assert cached2 == "feat: add feature 2"

    def test_same_diff_different_models(self, cache):
        """Test that same diff with different models have separate cache."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"
        model1 = "openai/gpt-4o"
        model2 = "anthropic/claude-3-sonnet"

        cache.set(diff, model1, "GPT-4 message")
        cache.set(diff, model2, "Claude message")

        cached1 = cache.get(diff, model1)
        cached2 = cache.get(diff, model2)

        assert cached1 == "GPT-4 message"
        assert cached2 == "Claude message"

    def test_cache_overwrite(self, cache):
        """Test that setting cache overwrites existing entry."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"
        model = "openai/gpt-4o"

        cache.set(diff, model, "First message")
        cache.set(diff, model, "Second message")

        cached = cache.get(diff, model)

        assert cached == "Second message"

    def test_cache_with_unicode(self, cache):
        """Test cache with unicode content."""
        diff = "diff --git a/test.py b/test.py\n+print('你好世界 🌍')"
        model = "openai/gpt-4o"
        message = "feat: add greeting in Chinese 你好"

        cache.set(diff, model, message)
        cached = cache.get(diff, model)

        assert cached == message

    def test_cache_with_very_long_content(self, cache):
        """Test cache with very long content."""
        diff = "diff --git a/test.py b/test.py\n" + "+line\n" * 10000
        model = "openai/gpt-4o"
        message = "feat: add many lines"

        cache.set(diff, model, message)
        cached = cache.get(diff, model)

        assert cached == message

    def test_cache_dir_creation(self, tmp_path):
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "nonexistent" / "cache"
        assert not cache_dir.exists()

        cache = CommitMessageCache(cache_dir=cache_dir)

        assert cache_dir.exists()

    def test_clear_expired_with_corrupted_files(self, cache):
        """Test clearing expired with some corrupted cache files."""
        # Add valid cache
        diff = "diff --git a/test.py b/test.py\n+print('hello')"
        cache.set(diff, "openai/gpt-4o", "feat: add feature")

        # Add corrupted file
        corrupted_path = cache.cache_dir / "corrupted.json"
        with open(corrupted_path, 'w') as f:
            f.write("invalid json")

        # Should handle gracefully
        count = cache.clear_expired()

        # Should have removed the corrupted file
        assert not corrupted_path.exists()

    def test_stats_calculation_accuracy(self, cache):
        """Test that stats are calculated accurately."""
        # Add known-size cache entries
        messages = [
            "feat: add feature 1",
            "fix: fix bug 2",
            "docs: update docs 3",
        ]

        for i, msg in enumerate(messages):
            diff = f"diff --git a/test{i}.py b/test{i}.py\n+print('{i}')"
            cache.set(diff, "openai/gpt-4o", msg)

        stats = cache.get_stats()

        assert stats['total_entries'] == 3
        # Check that MB calculation is reasonable
        assert stats['cache_size_mb'] == round(stats['cache_size_bytes'] / (1024 * 1024), 2)
