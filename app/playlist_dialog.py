from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox,
)

from data.database import Database
from data.models import Playlist


class PlaylistSelectionDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_playlist_id: int | None = None
        self._setup_ui()
        self._load_playlists()

    def _setup_ui(self):
        self.setWindowTitle("Add to Playlist")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a playlist:"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("+ New Playlist")
        self.new_btn.clicked.connect(self._create_new)
        btn_row.addWidget(self.new_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        layout.addLayout(btn_row)

    def _load_playlists(self):
        self.list_widget.clear()
        for pl in self.db.get_playlists():
            item = QListWidgetItem(f"{pl.name} ({pl.song_count} songs)")
            item.setData(1, pl.id)
            self.list_widget.addItem(item)

    def _create_new(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self.db.create_playlist(name.strip())
            self._load_playlists()

    def _accept(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_playlist_id = item.data(1)
            self.accept()
        else:
            self.reject()
