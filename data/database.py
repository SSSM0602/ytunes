import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from data.models import Song, Playlist


class Database:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(Path.home() / ".cache" / "ytunes" / "library.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT DEFAULT '',
                    duration INTEGER DEFAULT 0,
                    youtube_id TEXT UNIQUE,
                    thumbnail_url TEXT DEFAULT '',
                    local_path TEXT,
                    date_added TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    date_created TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS playlist_songs (
                    playlist_id INTEGER NOT NULL,
                    song_id INTEGER NOT NULL,
                    position INTEGER DEFAULT 0,
                    PRIMARY KEY (playlist_id, song_id),
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS search_cache (
                    query TEXT PRIMARY KEY,
                    results TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );
            """)
            self.conn.commit()

    # --- Songs ---

    def add_song(self, song: Song) -> int:
        with self._lock:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO songs (title, artist, duration, youtube_id, thumbnail_url, local_path) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (song.title, song.artist, song.duration, song.youtube_id, song.thumbnail_url, song.local_path)
            )
            self.conn.commit()
            if cur.lastrowid:
                return cur.lastrowid
            row = self.conn.execute("SELECT id FROM songs WHERE youtube_id = ?", (song.youtube_id,)).fetchone()
            return row["id"] if row else 0

    def get_song_by_youtube_id(self, youtube_id: str) -> Song | None:
        row = self.conn.execute("SELECT * FROM songs WHERE youtube_id = ?", (youtube_id,)).fetchone()
        return Song(**dict(row)) if row else None

    def get_all_songs(self) -> list[Song]:
        rows = self.conn.execute("SELECT * FROM songs ORDER BY date_added DESC").fetchall()
        return [Song(**dict(r)) for r in rows]

    def get_downloaded_songs(self) -> list[Song]:
        rows = self.conn.execute(
            "SELECT * FROM songs WHERE local_path IS NOT NULL ORDER BY date_added DESC"
        ).fetchall()
        return [Song(**dict(r)) for r in rows]

    def update_local_path(self, song_id: int, path: str):
        with self._lock:
            self.conn.execute("UPDATE songs SET local_path = ? WHERE id = ?", (path, song_id))
            self.conn.commit()

    def delete_song(self, song_id: int):
        with self._lock:
            self.conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
            self.conn.commit()

    # --- Playlists ---

    def create_playlist(self, name: str, description: str = "") -> int:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO playlists (name, description) VALUES (?, ?)",
                (name, description)
            )
            self.conn.commit()
            return cur.lastrowid

    def get_playlists(self) -> list[Playlist]:
        rows = self.conn.execute("""
            SELECT p.*, COUNT(ps.song_id) as song_count
            FROM playlists p
            LEFT JOIN playlist_songs ps ON ps.playlist_id = p.id
            GROUP BY p.id
            ORDER BY p.date_created DESC
        """).fetchall()
        return [Playlist(**dict(r)) for r in rows]

    def get_playlist(self, playlist_id: int) -> Playlist | None:
        row = self.conn.execute("""
            SELECT p.*, COUNT(ps.song_id) as song_count
            FROM playlists p
            LEFT JOIN playlist_songs ps ON ps.playlist_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
        """, (playlist_id,)).fetchone()
        return Playlist(**dict(row)) if row else None

    def rename_playlist(self, playlist_id: int, name: str):
        with self._lock:
            self.conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (name, playlist_id))
            self.conn.commit()

    def delete_playlist(self, playlist_id: int):
        with self._lock:
            self.conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            self.conn.commit()

    def add_song_to_playlist(self, playlist_id: int, song_id: int):
        with self._lock:
            max_pos = self.conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_songs WHERE playlist_id = ?",
                (playlist_id,)
            ).fetchone()[0]
            self.conn.execute(
                "INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id, position) VALUES (?, ?, ?)",
                (playlist_id, song_id, max_pos)
            )
            self.conn.commit()

    def remove_song_from_playlist(self, playlist_id: int, song_id: int):
        with self._lock:
            self.conn.execute(
                "DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?",
                (playlist_id, song_id)
            )
            self.conn.commit()

    def get_playlist_songs(self, playlist_id: int) -> list[Song]:
        rows = self.conn.execute("""
            SELECT s.* FROM songs s
            JOIN playlist_songs ps ON ps.song_id = s.id
            WHERE ps.playlist_id = ?
            ORDER BY ps.position
        """, (playlist_id,)).fetchall()
        return [Song(**dict(r)) for r in rows]

    def reorder_playlist(self, playlist_id: int, song_ids: list[int]):
        with self._lock:
            self.conn.executemany(
                "UPDATE playlist_songs SET position = ? WHERE playlist_id = ? AND song_id = ?",
                [(i, playlist_id, sid) for i, sid in enumerate(song_ids)]
            )
            self.conn.commit()

    # --- Search Cache ---

    def get_cached_search(self, query: str, max_age_sec: int = 300) -> list[dict] | None:
        row = self.conn.execute(
            "SELECT results, timestamp FROM search_cache WHERE query = ?", (query.lower(),)
        ).fetchone()
        if row:
            age = datetime.now().timestamp() - row["timestamp"]
            if age < max_age_sec:
                return json.loads(row["results"])
        return None

    def cache_search(self, query: str, results: list[dict]):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO search_cache (query, results, timestamp) VALUES (?, ?, ?)",
                (query.lower(), json.dumps(results), datetime.now().timestamp())
            )
            self.conn.commit()

    def close(self):
        self.conn.close()
