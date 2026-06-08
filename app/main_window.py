import os
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStatusBar,
    QInputDialog, QMessageBox, QMenuBar, QFileDialog,
)

from app.search_tab import SearchTab
from app.library_tab import LibraryTab
from app.playlist_import_dialog import PlaylistImportDialog
from app.playlist_tab import PlaylistTab
from app.player_bar import PlayerBar
from core.player import Player
from core.ytdlp_client import YtDlpClient
from core.stream_manager import StreamManager
from core.download_manager import DownloadManager
from data.database import Database
from data.models import SearchResult, Song
from utils.cache import ThumbnailCache


class PlaylistImportWorker(QThread):
    playlist_fetched = pyqtSignal(str, str, list)
    error = pyqtSignal(str)

    def __init__(self, ytdlp: YtDlpClient, url: str):
        super().__init__()
        self.ytdlp = ytdlp
        self.url = url

    def run(self):
        try:
            title, description, entries = self.ytdlp.extract_playlist(self.url)
            if title is None:
                self.error.emit("Could not extract playlist from URL.")
            else:
                self.playlist_fetched.emit(title, description, entries)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yTunes")
        self.setMinimumSize(1000, 650)

        self.db = Database()
        self.ytdlp = YtDlpClient()
        self.thumb_cache = ThumbnailCache()
        self.stream_manager = StreamManager()
        self.player = Player()
        self.download_manager = DownloadManager(self.db)

        self._queue: list[Song | SearchResult] = []

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { padding: 8px 16px; }
        """)

        self.search_tab = SearchTab(self.ytdlp, self.db, self.thumb_cache)
        self.library_tab = LibraryTab(self.db, self.thumb_cache)
        self.playlist_tab = PlaylistTab(self.db, self.thumb_cache)

        self.tabs.addTab(self.search_tab, "🔍 Search")
        self.tabs.addTab(self.library_tab, "📚 Library")
        self.tabs.addTab(self.playlist_tab, "📋 Playlists")

        layout.addWidget(self.tabs, 1)

        self.player_bar = PlayerBar(self.player)
        layout.addWidget(self.player_bar)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        import_music_action = QAction("Import Music Folder...", self)
        import_music_action.triggered.connect(self._import_music)
        file_menu.addAction(import_music_action)
        import_playlist_action = QAction("Import Playlist from URL...", self)
        import_playlist_action.setShortcut("Ctrl+Shift+I")
        import_playlist_action.triggered.connect(self._import_playlist)
        file_menu.addAction(import_playlist_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        playback_menu = menubar.addMenu("Playback")
        play_pause_action = QAction("Play/Pause", self)
        play_pause_action.setShortcut("Space")
        play_pause_action.triggered.connect(self.player.toggle_pause)
        playback_menu.addAction(play_pause_action)

        view_menu = menubar.addMenu("View")
        clear_cache_action = QAction("Clear Thumbnail Cache", self)
        clear_cache_action.triggered.connect(self._clear_cache)
        view_menu.addAction(clear_cache_action)

    def _connect_signals(self):
        self.search_tab.play_requested.connect(self._play_search_result)
        self.search_tab.add_to_queue_requested.connect(self._add_to_queue)
        self.search_tab.download_requested.connect(self._download_result)

        self.library_tab.play_requested.connect(self._play_song)
        self.library_tab.add_to_queue_requested.connect(self._add_song_to_queue)

        self.playlist_tab.play_requested.connect(self._play_song)
        self.playlist_tab.add_to_queue_requested.connect(self._add_song_to_queue)

        self.player_bar.prev_btn.clicked.connect(self._play_previous)
        self.player_bar.next_btn.clicked.connect(self._play_next)
        self.player_bar.queue_btn.clicked.connect(self._show_queue)

    def _play_search_result(self, result: SearchResult):
        song = Song(
            title=result.title,
            artist=result.artist,
            duration=result.duration,
            youtube_id=result.youtube_id,
            thumbnail_url=result.thumbnail_url,
        )
        self._play(song)

    def _play_song(self, song: Song):
        if song.is_local and song.local_path and os.path.exists(song.local_path):
            self.player_bar.display_song(song.title, song.artist)
            self.player.play_file(song.local_path, song)
            self.status_bar.showMessage(f"Playing: {song.title}")
            return

        self._play(song)

    def _play(self, song: Song, url_override: str | None = None):
        cached_url = self.stream_manager.get_cached_url(song.youtube_id)
        if cached_url:
            self.player_bar.display_song(
                song.title, song.artist,
                self.thumb_cache.get(song.thumbnail_url)
            )
            self.player.play_url(cached_url, song)
            self.status_bar.showMessage(f"Playing: {song.title}")
            return

        if url_override:
            url = url_override
        else:
            url = self.ytdlp.get_audio_url(song.youtube_id)

        if not url:
            resolved = self.ytdlp.resolve_stream_url(song.youtube_id)
            url = resolved

        if url:
            self.stream_manager.cache_url(song.youtube_id, url)
            self.player_bar.display_song(
                song.title, song.artist,
                self.thumb_cache.get(song.thumbnail_url)
            )
            self.player.play_url(url, song)
            self.status_bar.showMessage(f"Playing: {song.title}")

            if not self.thumb_cache.get(song.thumbnail_url):
                self.thumb_cache.fetch(song.thumbnail_url)
        else:
            QMessageBox.warning(self, "Playback Error",
                                f"Could not resolve stream URL for {song.title}")

    def _add_to_queue(self, result: SearchResult):
        self._queue.append(result)
        self.status_bar.showMessage(f"Added to queue ({len(self._queue)} queued)")

    def _add_song_to_queue(self, song: Song):
        self._queue.append(song)
        self.status_bar.showMessage(f"Added to queue ({len(self._queue)} queued)")

    def _play_previous(self):
        pass

    def _play_next(self):
        if self._queue:
            next_item = self._queue.pop(0)
            if isinstance(next_item, SearchResult):
                self._play_search_result(next_item)
            else:
                self._play_song(next_item)
        else:
            self.status_bar.showMessage("Queue is empty")

    def _show_queue(self):
        songs = []
        for item in self._queue:
            if isinstance(item, SearchResult):
                songs.append(f"{item.artist} - {item.title}")
            else:
                songs.append(f"{item.artist} - {item.title}")
        if songs:
            QMessageBox.information(self, "Queue",
                                    "\n".join(f"{i+1}. {s}" for i, s in enumerate(songs)))
        else:
            QMessageBox.information(self, "Queue", "Queue is empty")

    def _download_result(self, result: SearchResult):
        song = Song(
            title=result.title,
            artist=result.artist,
            duration=result.duration,
            youtube_id=result.youtube_id,
            thumbnail_url=result.thumbnail_url,
        )
        self.download_manager.download(song)
        self.status_bar.showMessage(f"Downloading: {song.title}")

    def _import_music(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder:
            count = 0
            for f in Path(folder).rglob("*"):
                if f.suffix.lower() in (".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"):
                    song = Song(
                        title=f.stem,
                        artist="Unknown",
                        duration=0,
                        youtube_id=f"local_{f.stem}",
                        local_path=str(f),
                    )
                    self.db.add_song(song)
                    count += 1
            self.library_tab.refresh()
            self.status_bar.showMessage(f"Imported {count} songs")

    def _import_playlist(self):
        url, ok = QInputDialog.getText(self, "Import Playlist from URL",
                                        "Paste a YouTube or YouTube Music playlist URL:")
        if not ok or not url.strip():
            return
        url = url.strip()

        self.status_bar.showMessage("Fetching playlist info...")
        self._import_worker = PlaylistImportWorker(self.ytdlp, url)
        self._import_worker.playlist_fetched.connect(self._on_playlist_fetched)
        self._import_worker.error.connect(self._on_import_error)
        self._import_worker.start()

    def _on_playlist_fetched(self, title: str, description: str, entries: list):
        self.status_bar.showMessage(f"Playlist fetched: {title} ({len(entries)} songs)")
        dialog = PlaylistImportDialog(title, description, entries, self.thumb_cache, self)
        if dialog.exec() != PlaylistImportDialog.DialogCode.Accepted:
            self.status_bar.showMessage("Playlist import cancelled")
            return

        existing_names = {pl.name for pl in self.db.get_playlists()}
        unique_name = title
        if unique_name in existing_names:
            suffix = 2
            while f"{title} ({suffix})" in existing_names:
                suffix += 1
            unique_name = f"{title} ({suffix})"

        pl_id = self.db.create_playlist(unique_name, description)
        imported = 0
        for entry in entries:
            song = Song(
                title=entry.title,
                artist=entry.artist,
                duration=entry.duration,
                youtube_id=entry.youtube_id,
                thumbnail_url=entry.thumbnail_url,
            )
            song_id = self.db.add_song(song)
            self.db.add_song_to_playlist(pl_id, song_id)
            imported += 1

        self.playlist_tab.refresh()
        self.tabs.setCurrentIndex(2)
        self.status_bar.showMessage(f"Imported playlist: {unique_name} ({imported} songs)")

    def _on_import_error(self, msg: str):
        QMessageBox.warning(self, "Import Error", f"Failed to import playlist:\n{msg}")
        self.status_bar.showMessage("Playlist import failed")

    def _clear_cache(self):
        self.thumb_cache.clear()
        self.status_bar.showMessage("Thumbnail cache cleared")

    def closeEvent(self, event):
        self.player.cleanup()
        self.db.close()
        event.accept()
