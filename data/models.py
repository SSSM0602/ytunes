from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Song:
    id: int = 0
    title: str = ""
    artist: str = ""
    duration: int = 0
    youtube_id: str = ""
    thumbnail_url: str = ""
    local_path: str | None = None
    date_added: str = ""

    @property
    def is_local(self) -> bool:
        return bool(self.local_path)

    @property
    def duration_str(self) -> str:
        from utils.format_utils import format_duration
        return format_duration(self.duration)


@dataclass
class Playlist:
    id: int = 0
    name: str = ""
    description: str = ""
    date_created: str = ""
    song_count: int = 0


@dataclass
class SearchResult:
    title: str
    artist: str
    duration: int
    youtube_id: str
    thumbnail_url: str
    url: str

    @property
    def duration_str(self) -> str:
        from utils.format_utils import format_duration
        return format_duration(self.duration)
