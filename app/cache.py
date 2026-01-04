"""
MAE-IDP OCR Cache
Hash-based caching to avoid re-processing identical documents
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import threading


@dataclass
class CacheEntry:
    """Cached OCR result"""
    file_hash: str
    result: Dict[str, Any]
    created_at: float
    hits: int = 0


class OCRCache:
    """
    Simple file-based cache for OCR results.
    Uses SHA-256 hash of file content as key.
    """

    def __init__(
        self,
        cache_dir: Path = None,
        max_entries: int = 1000,
        ttl_hours: int = 24 * 7  # 1 week default
    ):
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self.ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._load_cache()

    def _cache_file(self) -> Path:
        return self.cache_dir / "ocr_cache.json"

    def _load_cache(self):
        """Load cache from disk"""
        cache_file = self._cache_file()
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                now = time.time()
                for key, entry in data.items():
                    # Skip expired entries
                    if now - entry.get("created_at", 0) < self.ttl_seconds:
                        self._memory_cache[key] = CacheEntry(
                            file_hash=key,
                            result=entry.get("result", {}),
                            created_at=entry.get("created_at", now),
                            hits=entry.get("hits", 0)
                        )
            except (json.JSONDecodeError, KeyError):
                self._memory_cache = {}

    def _save_cache(self):
        """Save cache to disk"""
        cache_file = self._cache_file()
        data = {
            key: asdict(entry)
            for key, entry in self._memory_cache.items()
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content"""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _evict_old_entries(self):
        """Remove oldest entries if cache is too large"""
        if len(self._memory_cache) <= self.max_entries:
            return

        # Sort by hits (LFU) then by created_at (LRU)
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: (x[1].hits, x[1].created_at)
        )

        # Remove oldest 20%
        to_remove = len(self._memory_cache) - int(self.max_entries * 0.8)
        for key, _ in sorted_entries[:to_remove]:
            del self._memory_cache[key]

    def get(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get cached result for file.
        Returns None if not cached or expired.
        """
        file_hash = self._compute_hash(file_path)

        with self._lock:
            entry = self._memory_cache.get(file_hash)
            if entry is None:
                return None

            # Check TTL
            if time.time() - entry.created_at > self.ttl_seconds:
                del self._memory_cache[file_hash]
                return None

            # Update hit count
            entry.hits += 1
            return entry.result.copy()

    def set(self, file_path: Path, result: Dict[str, Any]):
        """Cache OCR result for file"""
        file_hash = self._compute_hash(file_path)

        with self._lock:
            self._memory_cache[file_hash] = CacheEntry(
                file_hash=file_hash,
                result=result.copy(),
                created_at=time.time(),
                hits=0
            )
            self._evict_old_entries()
            self._save_cache()

    def invalidate(self, file_path: Path):
        """Remove file from cache"""
        file_hash = self._compute_hash(file_path)
        with self._lock:
            if file_hash in self._memory_cache:
                del self._memory_cache[file_hash]
                self._save_cache()

    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._memory_cache.clear()
            cache_file = self._cache_file()
            if cache_file.exists():
                cache_file.unlink()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_hits = sum(e.hits for e in self._memory_cache.values())
            return {
                "entries": len(self._memory_cache),
                "max_entries": self.max_entries,
                "total_hits": total_hits,
                "ttl_hours": self.ttl_seconds // 3600,
                "cache_file": str(self._cache_file())
            }


# Global cache instance
_cache: Optional[OCRCache] = None


def get_cache() -> OCRCache:
    """Get or create global cache instance"""
    global _cache
    if _cache is None:
        _cache = OCRCache()
    return _cache
