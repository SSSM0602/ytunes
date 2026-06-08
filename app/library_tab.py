from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QMenu,
)

from data.database import Database
from data.models import Song
from utils.cache import ThumbnailCache


class LibraryTab(QWidget):
    play_requested = pyqtSignal(Song)
    add_to_queue_requested = pyqtSignal(Song)

    def __init__(self, db: Database, thumb_cache: ThumbnailCache, parent=None):
        super().__init__(parent)
        self.db = db
        self.thumb_cache = thumb_cache
        self._songs: list[Song] = []
        self._setup_ui()
        self._load_songs()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter library...")
        self.filter_input.setStyleSheet("padding: 8px 12px;")
        self.filter_input.textChanged.connect(self._filter_songs)
        filter_layout.addWidget(self.filter_input, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_songs)
        filter_layout.addWidget(self.refresh_btn)

        self.dl_only_btn = QPushButton("Show Downloaded")
        self.dl_only_btn.setCheckable(True)
        self.dl_only_btn.clicked.connect(self._load_songs)
        filter_layout.addWidget(self.dl_only_btn)

        layout.addLayout(filter_layout)

        self.song_list = QListWidget()
        self.song_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.song_list.customContextMenuRequested.connect(self._show_context_menu)
        self.song_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.song_list, 1)

    def _load_songs(self):
        if self.dl_only_btn.isChecked():
            self._songs = self.db.get_downloaded_songs()
            self.dl_only_btn.setText("Showing Downloaded")
        else:
            self._songs = self.db.get_all_songs()
            self.dl_only_btn.setText("All Songs")
        self._populate_songs()

    def _populate_songs(self, filter_text: str = ""):
        self.song_list.clear()
        filter_lower = filter_text.lower()
        for song in self._songs:
            if filter_lower and filter_lower not in song.title.lower() and filter_lower not in song.artist.lower():
                continue

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
            info_label = QLabel(song.artist)
            info_label.setStyleSheet("color: gray; font-size: 11px;")
            info_layout.addWidget(title_label)
            info_layout.addWidget(info_label)
            layout.addLayout(info_layout, 1)

            status = "💾" if song.is_local else "☁️"
            status_label = QLabel(status)
            status_label.setToolTip("Downloaded" if song.is_local else "Stream only")
            layout.addWidget(status_label)

            dur_label = QLabel(song.duration_str)
            dur_label.setStyleSheet("color: gray; font-size: 11px;")
            layout.addWidget(dur_label)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(1, song)
            self.song_list.addItem(item)
            self.song_list.setItemWidget(item, widget)

    def _filter_songs(self, text: str):
        self._populate_songs(text)

    def _show_context_menu(self, pos):
        item = self.song_list.itemAt(pos)
        if not item:
            return
        song: Song = item.data(1)
        menu = QMenu(self)
        play_action = menu.addAction("Play Now")
        queue_action = menu.addAction("Add to Queue")
        if song.is_local:
            menu.addAction(f"Local: {song.local_path}").setEnabled(False)
        action = menu.exec(self.song_list.mapToGlobal(pos))
        if action == play_action:
            self.play_requested.emit(song)
        elif action == queue_action:
            self.add_to_queue_requested.emit(song)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        song: Song = item.data(1)
        self.play_requested.emit(song)

    def refresh(self):
        self._load_songs()
