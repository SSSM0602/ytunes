import re
import threading

from yt_dlp import YoutubeDL

from data.models import SearchResult


class YtDlpClient:
    def __init__(self):
        self._lock = threading.Lock()

    def _ydl_opts(self) -> dict:
        return {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
            "default_search": "ytsearch20",
            "source_address": "0.0.0.0",
            "extractor_args": {"youtube": {"search_source": ["ytmusic"]}},
        }

    @staticmethod
    def _topic_score(uploader: str) -> int:
        if not uploader:
            return 0
        if uploader.endswith(" - Topic"):
            return 3
        if "VEVO" in uploader.upper():
            return 2
        return 1

    @staticmethod
    def _clean_artist(uploader: str) -> str:
        if uploader and uploader.endswith(" - Topic"):
            return uploader[:-8]
        return uploader or "Unknown"

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        opts = self._ydl_opts()
        opts["extract_flat"] = True
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            if not info or "entries" not in info:
                return []
            raw: list[tuple[str, dict]] = []
            for entry in info["entries"]:
                if not entry:
                    continue
                raw.append((entry.get("uploader", "Unknown"), entry))
            raw.sort(key=lambda x: self._topic_score(x[0]), reverse=True)
            results = []
            for uploader, entry in raw:
                results.append(SearchResult(
                    title=entry.get("title", "Unknown"),
                    artist=self._clean_artist(uploader),
                    duration=entry.get("duration", 0) or 0,
                    youtube_id=entry.get("id", ""),
                    thumbnail_url=entry.get("thumbnail", "") or "",
                    url=f"https://youtube.com/watch?v={entry.get('id', '')}",
                ))
            return results

    def extract_audio_url(self, url: str) -> str | None:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "extract_flat": False,
            "ignoreerrors": True,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            best = info.get("url")
            if not best and "formats" in info:
                for f in info["formats"]:
                    if f.get("acodec") and f["acodec"] != "none":
                        best = f.get("url") or best
            return best

    def resolve_stream_url(self, youtube_id: str) -> str | None:
        return self.extract_audio_url(f"https://youtube.com/watch?v={youtube_id}")

    def get_audio_url(self, youtube_id: str) -> str | None:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "ignoreerrors": True,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://youtube.com/watch?v={youtube_id}", download=False)
            if not info:
                return None
            return info.get("url") or self._find_best_audio_url(info)

    def _find_best_audio_url(self, info: dict) -> str | None:
        formats = info.get("formats") or []
        for fmt in formats:
            acodec = fmt.get("acodec", "")
            if acodec and acodec != "none":
                url = fmt.get("url")
                if url:
                    return url
        return info.get("url")

    def extract_info(self, youtube_id: str) -> dict | None:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "ignoreerrors": True,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://youtube.com/watch?v={youtube_id}", download=False)
            return info

    def extract_playlist(self, url: str) -> tuple[str | None, str, list[SearchResult]]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "source_address": "0.0.0.0",
        }
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info or "entries" not in info:
                    return None, "", []
                title = info.get("title", "Imported Playlist")
                description = info.get("description", "")
                entries: list[SearchResult] = []
                seen: set[str] = set()
                for entry in info["entries"]:
                    if not entry or not entry.get("id"):
                        continue
                    vid = entry["id"]
                    if vid in seen:
                        continue
                    seen.add(vid)
                    uploader = entry.get("uploader") or entry.get("channel", "Unknown")
                    entries.append(SearchResult(
                        title=entry.get("title", "Unknown"),
                        artist=self._clean_artist(uploader),
                        duration=entry.get("duration", 0) or 0,
                        youtube_id=vid,
                        thumbnail_url=entry.get("thumbnail") or entry.get("thumbnails", [{}])[0].get("url", ""),
                        url=f"https://youtube.com/watch?v={vid}",
                    ))
                return title, description, entries
        except Exception:
            return None, "", []
