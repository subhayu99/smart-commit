"""Caching layer for commit messages."""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional


class CommitMessageCache:
    """Cache for generated commit messages to avoid redundant API calls."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files. Defaults to ~/.cache/smart-commit/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "smart-commit"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache expiry time in seconds (24 hours)
        self.expiry_time = 24 * 60 * 60

    def _get_cache_key(self, diff_content: str, model: str) -> str:
        """
        Generate cache key from diff content and model.

        Args:
            diff_content: The git diff content
            model: AI model being used

        Returns:
            Cache key (hash)
        """
        # Create a hash of the diff content and model
        content = f"{model}:{diff_content}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, diff_content: str, model: str) -> Optional[str]:
        """
        Get cached commit message.

        Args:
            diff_content: The git diff content
            model: AI model being used

        Returns:
            Cached commit message if found and not expired, None otherwise
        """
        cache_key = self._get_cache_key(diff_content, model)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache has expired
            if time.time() - cache_data.get('timestamp', 0) > self.expiry_time:
                # Cache expired, remove it
                cache_path.unlink()
                return None

            return cache_data.get('message')

        except (json.JSONDecodeError, KeyError, Exception):
            # Invalid cache file, remove it
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(self, diff_content: str, model: str, message: str) -> None:
        """
        Store commit message in cache.

        Args:
            diff_content: The git diff content
            model: AI model used
            message: Generated commit message
        """
        cache_key = self._get_cache_key(diff_content, model)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            'message': message,
            'model': model,
            'timestamp': time.time(),
        }

        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            # Silently fail if we can't write cache
            pass

    def clear(self) -> int:
        """
        Clear all cached messages.

        Returns:
            Number of cache files removed
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass
        return count

    def clear_expired(self) -> int:
        """
        Clear expired cache entries.

        Returns:
            Number of expired cache files removed
        """
        count = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)

                if current_time - cache_data.get('timestamp', 0) > self.expiry_time:
                    cache_file.unlink()
                    count += 1
            except Exception:
                # If we can't read it, remove it
                try:
                    cache_file.unlink()
                    count += 1
                except Exception:
                    pass

        return count

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (total_entries, cache_size_bytes)
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files if f.exists())

        return {
            'total_entries': len(cache_files),
            'cache_size_bytes': total_size,
            'cache_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir),
        }
