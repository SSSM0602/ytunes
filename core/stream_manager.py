import threading
import time


class StreamManager:
    def __init__(self):
        self._cache: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._ttl = 3600

    def get_cached_url(self, youtube_id: str) -> str | None:
        with self._lock:
            entry = self._cache.get(youtube_id)
            if entry:
                url, ts = entry
                if time.time() - ts < self._ttl:
                    return url
                del self._cache[youtube_id]
            return None

    def cache_url(self, youtube_id: str, url: str):
        with self._lock:
            self._cache[youtube_id] = (url, time.time())

    def invalidate(self, youtube_id: str):
        with self._lock:
            self._cache.pop(youtube_id, None)

    def clear(self):
        with self._lock:
            self._cache.clear()
