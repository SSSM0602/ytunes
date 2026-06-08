from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QSlider, QWidget, QSizePolicy,
)

from utils.format_utils import format_duration


class PlayerBar(QFrame):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self._setup_ui()
        self._connect_signals()
        self._setup_timer()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(90)
        self.setStyleSheet("""
            PlayerBar {
                background: palette(window);
                border-top: 1px solid palette(mid);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(60, 60)
        self.thumb_label.setScaledContents(True)
        self.thumb_label.setStyleSheet("background: palette(mid); border-radius: 4px;")
        layout.addWidget(self.thumb_label)

        info_layout = QVBoxLayout()
        self.title_label = QLabel("No track playing")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.artist_label = QLabel("")
        self.artist_label.setStyleSheet("color: palette(disabled); font-size: 11px;")
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)

        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(4)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setToolTip("Previous")
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setToolTip("Play/Pause")
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setToolTip("Next")

        for btn in (self.prev_btn, self.play_btn, self.next_btn):
            btn.setStyleSheet("""
                QPushButton {
                    border: none; font-size: 18px;
                    background: transparent;
                }
                QPushButton:hover { color: palette(highlight); }
            """)
        btn_layout.addStretch()
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.play_btn)
        btn_layout.addWidget(self.next_btn)
        btn_layout.addStretch()

        seek_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet("font-size: 11px;")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.total_label = QLabel("0:00")
        self.total_label.setStyleSheet("font-size: 11px;")
        seek_layout.addWidget(self.time_label)
        seek_layout.addWidget(self.seek_slider, 1)
        seek_layout.addWidget(self.total_label)

        controls_layout.addLayout(btn_layout)
        controls_layout.addLayout(seek_layout)
        layout.addLayout(controls_layout, 2)

        vol_layout = QHBoxLayout()
        mute_btn = QPushButton("🔊")
        mute_btn.setFixedSize(24, 24)
        mute_btn.setStyleSheet("border: none; font-size: 14px; background: transparent;")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        vol_layout.addWidget(mute_btn)
        vol_layout.addWidget(self.vol_slider)
        layout.addLayout(vol_layout)

        self.queue_btn = QPushButton("Queue")
        self.queue_btn.setStyleSheet("""
            QPushButton { padding: 6px 12px; border: 1px solid palette(mid);
                          border-radius: 4px; background: transparent; }
            QPushButton:hover { background: palette(highlight); color: white; }
        """)
        layout.addWidget(self.queue_btn)

    def _connect_signals(self):
        self.play_btn.clicked.connect(self._on_play_pause)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)

    def _setup_timer(self):
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._update_progress)
        self._timer.start()
        self._seeking = False

    def _on_play_pause(self):
        self.player.toggle_pause()

    def _on_seek_start(self):
        self._seeking = True

    def _on_seek_end(self):
        pos = self.seek_slider.value() / 1000.0
        self.player.seek(pos)
        self._seeking = False

    def _on_volume_changed(self, vol):
        self.player.set_volume(vol)

    def _update_progress(self):
        if not self._seeking:
            pos = self.player.get_position()
            self.seek_slider.setValue(int(pos * 1000))

        time_ms = self.player.get_time()
        length_ms = self.player.get_length()
        self.time_label.setText(format_duration(time_ms // 1000) if time_ms > 0 else "0:00")
        self.total_label.setText(format_duration(length_ms // 1000) if length_ms > 0 else "0:00")

        state = self.player.state
        if state == "playing":
            self.play_btn.setText("⏸")
        elif state == "paused":
            self.play_btn.setText("▶")
        else:
            self.play_btn.setText("▶")

    def display_song(self, title: str, artist: str, thumb_path: str | None = None):
        self.title_label.setText(title)
        self.artist_label.setText(artist)
        if thumb_path:
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                self.thumb_label.setPixmap(pixmap)
        else:
            self.thumb_label.clear()
