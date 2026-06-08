from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QInputDialog, QMessageBox,
    QMenu,
)

from data.database import Database
from data.models import Playlist, Song
from utils.cache import ThumbnailCache
from app.playlist_dialog import PlaylistSelectionDialog


class PlaylistTab(QWidget):
    play_requested = pyqtSignal(Song)
    add_to_queue_requested = pyqtSignal(Song)

    def __init__(self, db: Database, thumb_cache: ThumbnailCache, parent=None):
        super().__init__(parent)
        self.db = db
        self.thumb_cache = thumb_cache
        self._current_playlist_id: int | None = None
        self._current_songs: list[Song] = []
        self._setup_ui()
        self._load_playlists()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.new_pl_btn = QPushButton("+ New Playlist")
        self.new_pl_btn.clicked.connect(self._create_playlist)
        left_layout.addWidget(self.new_pl_btn)

        self.playlist_list = QListWidget()
        self.playlist_list.setStyleSheet("""
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background: palette(highlight); color: white; }
        """)
        self.playlist_list.currentRowChanged.connect(self._on_playlist_selected)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._playlist_context_menu)
        left_layout.addWidget(self.playlist_list, 1)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.header_label = QLabel("Select a playlist")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        right_layout.addWidget(self.header_label)

        self.song_list = QListWidget()
        self.song_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.song_list.customContextMenuRequested.connect(self._song_context_menu)
        self.song_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        right_layout.addWidget(self.song_list, 1)

        splitter.addWidget(right_widget)
        splitter.setSizes([200, 500])

        layout.addWidget(splitter, 1)

    def _load_playlists(self):
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        for pl in self.db.get_playlists():
            item = QListWidgetItem(f"{pl.name} ({pl.song_count})")
            item.setData(1, pl.id)
            self.playlist_list.addItem(item)
        self.playlist_list.blockSignals(False)

    def _on_playlist_selected(self, index: int):
        item = self.playlist_list.item(index)
        if not item:
            self._current_playlist_id = None
            self.header_label.setText("Select a playlist")
            self.song_list.clear()
            return

        self._current_playlist_id = item.data(1)
        pl = self.db.get_playlist(self._current_playlist_id)
        self.header_label.setText(pl.name if pl else "Playlist")
        self._load_songs()

    def _load_songs(self):
        self.song_list.clear()
        if not self._current_playlist_id:
            return
        self._current_songs = self.db.get_playlist_songs(self._current_playlist_id)
        for song in self._current_songs:
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(8, 6, 8, 6)

            thumb_label = QLabel()
            thumb_label.setFixedSize(40, 40)
            thumb_label.setScaledContents(True)
            thumb_label.setStyleSheet("background: palette(mid); border-radius: 3px;")
            if song.thumbnail_url:
                path = self.thumb_cache.get(song.thumbnail_url)
                if path:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        thumb_label.setPixmap(pixmap)
            layout.addWidget(thumb_label)

            info_layout = QVBoxLayout()
            title_label = QLabel(song.title)
            title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
            artist_label = QLabel(song.artist)
            artist_label.setStyleSheet("color: gray; font-size: 11px;")
            info_layout.addWidget(title_label)
            info_layout.addWidget(artist_label)
            layout.addLayout(info_layout, 1)

            dur_label = QLabel(song.duration_str)
            dur_label.setStyleSheet("color: gray; font-size: 11px;")
            layout.addWidget(dur_label)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(1, song)
            self.song_list.addItem(item)
            self.song_list.setItemWidget(item, widget)

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self.db.create_playlist(name.strip())
            self._load_playlists()

    def _playlist_context_menu(self, pos):
        item = self.playlist_list.itemAt(pos)
        if not item:
            return
        pl_id = item.data(1)
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        action = menu.exec(self.playlist_list.mapToGlobal(pos))
        if action == rename_action:
            name, ok = QInputDialog.getText(self, "Rename Playlist", "New name:")
            if ok and name.strip():
                self.db.rename_playlist(pl_id, name.strip())
                self._load_playlists()
                self._on_playlist_selected(self.playlist_list.currentRow())
        elif action == delete_action:
            reply = QMessageBox.question(self, "Delete Playlist",
                                          "Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_playlist(pl_id)
                self._load_playlists()
                self.song_list.clear()
                self.header_label.setText("Select a playlist")

    def _song_context_menu(self, pos):
        item = self.song_list.itemAt(pos)
        if not item:
            return
        song: Song = item.data(1)
        menu = QMenu(self)
        play_action = menu.addAction("Play Now")
        queue_action = menu.addAction("Add to Queue")
        menu.addSeparator()
        remove_action = menu.addAction("Remove from Playlist")
        action = menu.exec(self.song_list.mapToGlobal(pos))
        if action == play_action:
            self.play_requested.emit(song)
        elif action == queue_action:
            self.add_to_queue_requested.emit(song)
        elif action == remove_action:
            if self._current_playlist_id:
                db_song = self.db.get_song_by_youtube_id(song.youtube_id)
                if db_song:
                    self.db.remove_song_from_playlist(self._current_playlist_id, db_song.id)
                    self._load_songs()
                    self._load_playlists()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        song: Song = item.data(1)
        self.play_requested.emit(song)

    def refresh(self):
        self._load_playlists()
        self._load_songs()
