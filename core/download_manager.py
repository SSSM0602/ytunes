import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from data.database import Database
from data.models import Song


class DownloadManager:
    def __init__(self, db: Database, download_dir: str | None = None):
        self.db = db
        if download_dir is None:
            download_dir = str(Path.home() / "Music" / "ytunes")
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._active: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._listeners: dict[str, list[callable]] = {
            "progress": [],
            "completed": [],
            "error": [],
        }

    def on(self, event: str, callback: callable):
        if event in self._listeners:
            self._listeners[event].append(callback)

    def _emit(self, event: str, *args):
        for cb in self._listeners.get(event, []):
            cb(*args)

    def download(self, song: Song):
        youtube_id = song.youtube_id
        with self._lock:
            if youtube_id in self._active:
                return
            self._active[youtube_id] = {
                "progress": 0,
                "status": "starting",
                "song": song,
                "cancelled": False,
            }

        thread = threading.Thread(target=self._download_worker, args=(song,), daemon=True)
        thread.start()

    def cancel(self, youtube_id: str):
        with self._lock:
            entry = self._active.get(youtube_id)
            if entry:
                entry["cancelled"] = True

    def get_status(self, youtube_id: str) -> dict | None:
        with self._lock:
            entry = self._active.get(youtube_id)
            return dict(entry) if entry else None

    def _sanitize_filename(self, name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in " ._-()").strip()

    def _download_worker(self, song: Song):
        safe_title = self._sanitize_filename(song.title)
        safe_artist = self._sanitize_filename(song.artist)
        filename = f"{safe_artist} - {safe_title}.%(ext)s"
        output_path = str(self.download_dir / filename)

        try:
            self._update_status(song.youtube_id, "downloading", 0)

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_path,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "progress_hooks": [self._make_progress_hook(song.youtube_id)],
            }

            from yt_dlp import YoutubeDL
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://youtube.com/watch?v={song.youtube_id}"])

            final_path = None
            for ext in ["mp3", "m4a", "webm", "opus"]:
                p = self.download_dir / f"{safe_artist} - {safe_title}.{ext}"
                if p.exists():
                    final_path = str(p)
                    break

            if final_path:
                self.db.add_song(song)
                db_song = self.db.get_song_by_youtube_id(song.youtube_id)
                if db_song:
                    self.db.update_local_path(db_song.id, final_path)
                self._update_status(song.youtube_id, "completed", 100)
                self._emit("completed", song, final_path)
            else:
                raise Exception("Output file not found after download")

        except Exception as e:
            self._update_status(song.youtube_id, "error", 0)
            self._emit("error", song, str(e))
        finally:
            with self._lock:
                self._active.pop(song.youtube_id, None)

    def _make_progress_hook(self, youtube_id: str):
        def hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = int(downloaded * 100 / total)
                    self._update_status(youtube_id, "downloading", pct)
            elif d.get("status") == "finished":
                self._update_status(youtube_id, "processing", 0)
        return hook

    def _update_status(self, youtube_id: str, status: str, progress: int):
        with self._lock:
            entry = self._active.get(youtube_id)
            if entry:
                entry["status"] = status
                entry["progress"] = progress
        self._emit("progress", youtube_id, status, progress)
