# yTunes

A desktop YouTube music player built with PyQt6 and VLC. Search YouTube Music, stream audio, build playlists, and download songs for offline playback.

## Features

- Search YouTube Music with automatic Topic channel prioritization
- Stream audio from YouTube without downloading
- Download songs for offline playback (MP3 192kbps)
- Create and manage playlists with Play All / Shuffle Play
- Continuous playlist playback with auto-advance
- Shuffle mode
- Repeat modes: Off / All / One
- Local music library with search and filter
- Import local music folders
- Import YouTube / YouTube Music playlists by URL
- Thumbnail caching
- Native desktop integration (`.desktop` file, app menu launcher)

## Installation

### Pre-built executables

Download the latest archive for your platform from the [Releases](https://github.com/SSSM0602/ytunes/releases) page:

| Platform | Archive | Extract |
|----------|---------|---------|
| Linux x86_64 | `ytunes-linux-x86_64.tar.gz` | `tar xzf ytunes-linux-x86_64.tar.gz` |
| macOS (Apple Silicon) | `ytunes-macos-arm64.tar.gz` | `tar xzf ytunes-macos-arm64.tar.gz` |
| Windows x86_64 | `ytunes-windows-x86_64.tar.gz` | Extract with 7-Zip or similar |

Each archive contains a standalone executable with VLC bundled inside. No additional runtime dependencies are required. Releases are automatically built by GitHub Actions when a version tag is pushed.

### Run from source

Requires Python 3.12+ and VLC installed on your system.

```bash
git clone https://github.com/SSSM0602/ytunes.git
cd ytunes
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
python main.py
```

## Build your own executable

Build scripts are provided for each platform:

```bash
# Linux
bash scripts/build-linux.sh

# macOS (requires VLC in /Applications/VLC.app)
bash scripts/build-macos.sh

# Windows (requires VLC in C:\Program Files\VideoLAN\VLC)
scripts\build-windows.bat
```

The output is a single, portable executable at `build/pyinstaller/ytunes` (or `ytunes.exe` on Windows) with VLC bundled inside.

## How it works

yTunes uses yt-dlp to search and fetch audio streams from YouTube Music. Search results are sorted to prioritize official audio sources -- Topic channels first, then VEVO channels. Audio playback is handled by VLC via python-vlc bindings. Downloaded songs are stored locally and served from disk on subsequent plays.
