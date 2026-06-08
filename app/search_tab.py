from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QMenu, QMessageBox,
)

from core.ytdlp_client import YtDlpClient
from data.database import Database
from data.models import SearchResult, Song
from utils.cache import ThumbnailCache
from app.playlist_dialog import PlaylistSelectionDialog


class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client: YtDlpClient, query: str):
        super().__init__()
        self.client = client
        self.query = query

    def run(self):
        try:
            results = self.client.search(self.query)
            self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class SearchTab(QWidget):
    play_requested = pyqtSignal(SearchResult)
    add_to_queue_requested = pyqtSignal(SearchResult)
    download_requested = pyqtSignal(SearchResult)

    def __init__(self, ytdlp: YtDlpClient, db: Database, thumb_cache: ThumbnailCache, parent=None):
        super().__init__(parent)
        self.ytdlp = ytdlp
        self.db = db
        self.thumb_cache = thumb_cache
        self._results: list[SearchResult] = []
        self._worker: SearchWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for songs, artists, or albums...")
        self.search_input.setStyleSheet("padding: 8px 12px; font-size: 14px;")
        self.search_input.returnPressed.connect(self._do_search)
        self.search_btn = QPushButton("Search")
        self.search_btn.setStyleSheet("padding: 8px 20px;")
        self.search_btn.clicked.connect(self._do_search)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget::item { border-bottom: 1px solid palette(mid); }
            QListWidget::item:hover { background: palette(light); }
        """)
        self.result_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.result_list.customContextMenuRequested.connect(self._show_context_menu)
        self.result_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.result_list, 1)

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        cached = self.db.get_cached_search(query)
        if cached is not None:
            self._results = [SearchResult(**r) for r in cached]
            self._populate_results()
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("Searching...")
        self.result_list.clear()

        self._worker = SearchWorker(self.ytdlp, query)
        self._worker.results_ready.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(lambda: self.search_btn.setEnabled(True))
        self._worker.start()

    def _on_results(self, results: list[SearchResult]):
        self._results = results
        self._populate_results()

        query = self.search_input.text().strip()
        if results:
            self.db.cache_search(query, [r.__dict__ for r in results])

        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")

    def _on_error(self, msg: str):
        QMessageBox.warning(self, "Search Error", f"Search failed: {msg}")
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")

    def _populate_results(self):
        self.result_list.clear()
        for r in self._results:
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(8, 6, 8, 6)

            thumb_label = QLabel()
            thumb_label.setFixedSize(48, 48)
            thumb_label.setScaledContents(True)
            thumb_label.setStyleSheet("background: palette(mid); border-radius: 3px;")
            thumb_path = self.thumb_cache.get(r.thumbnail_url)
            if thumb_path:
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    thumb_label.setPixmap(pixmap)
            layout.addWidget(thumb_label)

            info_layout = QVBoxLayout()
            title_label = QLabel(r.title)
            title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
            artist_label = QLabel(r.artist)
            artist_label.setStyleSheet("color: gray; font-size: 11px;")
            info_layout.addWidget(title_label)
            info_layout.addWidget(artist_label)
            layout.addLayout(info_layout, 1)

            duration_label = QLabel(r.duration_str)
            duration_label.setStyleSheet("color: gray; font-size: 11px;")
            layout.addWidget(duration_label)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(1, r)
            self.result_list.addItem(item)
            self.result_list.setItemWidget(item, widget)

            if not thumb_path:
                self._load_thumbnail_async(item, thumb_label, r)

    def _load_thumbnail_async(self, item: QListWidgetItem, label: QLabel, result: SearchResult):
        from PyQt6.QtCore import QTimer
        def load():
            path = self.thumb_cache.fetch(result.thumbnail_url)
            if path:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    label.setPixmap(pixmap)
        QTimer.singleShot(100, load)

    def _show_context_menu(self, pos):
        item = self.result_list.itemAt(pos)
        if not item:
            return
        result: SearchResult = item.data(1)
        menu = QMenu(self)
        play_action = menu.addAction("Play Now")
        queue_action = menu.addAction("Add to Queue")
        dl_action = menu.addAction("Download")
        pl_action = menu.addAction("Add to Playlist...")

        action = menu.exec(self.result_list.mapToGlobal(pos))
        if action == play_action:
            self.play_requested.emit(result)
        elif action == queue_action:
            self.add_to_queue_requested.emit(result)
        elif action == dl_action:
            self.download_requested.emit(result)
        elif action == pl_action:
            dialog = PlaylistSelectionDialog(self.db, self)
            if dialog.exec() == PlaylistSelectionDialog.DialogCode.Accepted and dialog.selected_playlist_id:
                song = Song(
                    title=result.title,
                    artist=result.artist,
                    duration=result.duration,
                    youtube_id=result.youtube_id,
                    thumbnail_url=result.thumbnail_url,
                )
                song_id = self.db.add_song(song)
                self.db.add_song_to_playlist(dialog.selected_playlist_id, song_id)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        result: SearchResult = item.data(1)
        self.play_requested.emit(result)
