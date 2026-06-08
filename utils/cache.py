import io
import os
import hashlib
from pathlib import Path

import requests
from PIL import Image


class ThumbnailCache:
    def __init__(self, cache_dir: str | None = None):
        if cache_dir is None:
            cache_dir = os.path.join(Path.home(), ".cache", "ytunes", "thumbnails")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str, size: tuple[int, int] = (200, 200)) -> Path:
        key = hashlib.md5(f"{url}-{size[0]}x{size[1]}".encode()).hexdigest()
        return self.cache_dir / f"{key}.jpg"

    def get(self, url: str, size: tuple[int, int] = (200, 200)) -> str | None:
        path = self._path(url, size)
        if path.exists():
            return str(path)
        return None

    def fetch(self, url: str, size: tuple[int, int] = (200, 200)) -> str | None:
        cached = self.get(url, size)
        if cached:
            return cached

        try:
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "yTunes/1.0"
            })
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            img.thumbnail(size, Image.LANCZOS)
            path = self._path(url, size)
            img.save(path, "JPEG", quality=85)
            return str(path)
        except Exception:
            return None

    def clear(self) -> None:
        for f in self.cache_dir.iterdir():
            f.unlink()
