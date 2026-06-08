from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QWidget, QFrame,
)

from data.models import SearchResult
from utils.cache import ThumbnailCache
from utils.format_utils import format_duration


class PlaylistImportDialog(QDialog):
    def __init__(self, title: str, description: str, entries: list[SearchResult],
                 thumb_cache: ThumbnailCache, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Playlist")
        self.setMinimumSize(600, 450)
        self.resize(640, 500)
        self.setModal(True)
        self._entries = entries
        self._thumb_cache = thumb_cache
        self._setup_ui(title, description)

    def _setup_ui(self, title: str, description: str):
        layout = QVBoxLayout(self)

        header_label = QLabel(title)
        header_label.setStyleSheet("font-weight: bold; font-size: 16px; padding: 8px 0 4px 0;")
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: gray; font-size: 11px; padding: 0 0 4px 0;")
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(60)
            layout.addWidget(desc_label)

        count_label = QLabel(f"{len(self._entries)} songs")
        count_label.setStyleSheet("color: gray; font-size: 11px; padding: 0 0 8px 0;")
        layout.addWidget(count_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.song_list = QListWidget()
        self.song_list.setStyleSheet("""
            QListWidget::item { border-bottom: 1px solid palette(mid); }
            QListWidget::item:hover { background: palette(light); }
        """)
        self._populate_songs()
        layout.addWidget(self.song_list, 1)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator2)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        import_btn = QPushButton("Import")
        import_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px; font-weight: bold;
                background: palette(highlight); color: white;
                border-radius: 4px;
            }
            QPushButton:hover { background: palette(highlight); }
        """)
        import_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(import_btn)
        layout.addLayout(btn_layout)

    def _populate_songs(self):
        self.song_list.clear()
        for entry in self._entries:
            widget = QWidget()
            row_layout = QHBoxLayout(widget)
            row_layout.setContentsMargins(8, 6, 8, 6)

            thumb_label = QLabel()
            thumb_label.setFixedSize(40, 40)
            thumb_label.setScaledContents(True)
            thumb_label.setStyleSheet("background: palette(mid); border-radius: 3px;")
            if entry.thumbnail_url:
                path = self._thumb_cache.get(entry.thumbnail_url)
                if not path:
                    path = self._thumb_cache.fetch(entry.thumbnail_url)
                if path:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        thumb_label.setPixmap(pixmap)
            row_layout.addWidget(thumb_label)

            info_layout = QVBoxLayout()
            title_label = QLabel(entry.title)
            title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
            title_label.setWordWrap(True)
            artist_label = QLabel(entry.artist)
            artist_label.setStyleSheet("color: gray; font-size: 11px;")
            info_layout.addWidget(title_label)
            info_layout.addWidget(artist_label)
            row_layout.addLayout(info_layout, 1)

            dur_label = QLabel(format_duration(entry.duration) if entry.duration else "")
            dur_label.setStyleSheet("color: gray; font-size: 11px;")
            row_layout.addWidget(dur_label)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.song_list.addItem(item)
            self.song_list.setItemWidget(item, widget)
