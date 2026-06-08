import os
import threading
import time
from pathlib import Path

import vlc

from data.models import Song


class Player:
    STATE_STOPPED = "stopped"
    STATE_PLAYING = "playing"
    STATE_PAUSED = "paused"

    def __init__(self):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self._media: vlc.Media | None = None
        self._state = self.STATE_STOPPED
        self._current_song: Song | None = None
        self._lock = threading.Lock()
        self._listeners: dict[str, list[callable]] = {
            "state_changed": [],
            "position_changed": [],
            "song_finished": [],
            "error": [],
        }

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_song(self) -> Song | None:
        return self._current_song

    def on(self, event: str, callback: callable):
        if event in self._listeners:
            self._listeners[event].append(callback)

    def _emit(self, event: str, *args):
        for cb in self._listeners.get(event, []):
            cb(*args)

    def play_url(self, url: str, song: Song | None = None):
        with self._lock:
            self._media = self.instance.media_new(url)
            self.player.set_media(self._media)
            self._current_song = song
            self.player.play()
            self._state = self.STATE_PLAYING
            self._emit("state_changed", self._state)

    def play_file(self, path: str, song: Song | None = None):
        with self._lock:
            self._media = self.instance.media_new_path(path)
            self.player.set_media(self._media)
            self._current_song = song
            self.player.play()
            self._state = self.STATE_PLAYING
            self._emit("state_changed", self._state)

    def pause(self):
        self.player.pause()
        self._state = self.STATE_PAUSED
        self._emit("state_changed", self._state)

    def resume(self):
        self.player.play()
        self._state = self.STATE_PLAYING
        self._emit("state_changed", self._state)

    def toggle_pause(self):
        if self._state == self.STATE_PLAYING:
            self.pause()
        elif self._state == self.STATE_PAUSED:
            self.resume()
        else:
            pass

    def stop(self):
        self.player.stop()
        self._state = self.STATE_STOPPED
        self._current_song = None
        self._emit("state_changed", self._state)

    def seek(self, position: float):
        self.player.set_position(position)

    def set_volume(self, volume: int):
        self.player.audio_set_volume(max(0, min(100, volume)))

    def get_volume(self) -> int:
        return self.player.audio_get_volume()

    def get_position(self) -> float:
        return self.player.get_position() or 0.0

    def get_time(self) -> int:
        return self.player.get_time()

    def get_length(self) -> int:
        return self.player.get_length()

    def is_finished(self) -> bool:
        return self.player.get_state() == vlc.State.Ended

    def cleanup(self):
        self.stop()
        self.player.release()
        self.instance.release()
