#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Building yTunes for macOS arm64 (Apple Silicon)..."
echo "    Requires: VLC installed at /Applications/VLC.app"

VLC_BUNDLE="/Applications/VLC.app/Contents/MacOS"
VLC_LIBDIR="$VLC_BUNDLE/lib"

if [ ! -d "$VLC_LIBDIR" ]; then
    echo "ERROR: VLC not found at $VLC_BUNDLE"
    echo "       Install VLC from https://videolan.org"
    exit 1
fi

rm -rf build/pyinstaller build/pyinstaller-work

# Find the VLC plugins directory
VLC_PLUGINS=""
for d in "$VLC_BUNDLE/modules" "$VLC_BUNDLE/plugins"; do
    if [ -d "$d" ]; then
        VLC_PLUGINS="$d"
        break
    fi
done

# Build VLC plugin path arg
VLC_DATA_ARGS=""
if [ -n "$VLC_PLUGINS" ]; then
    VLC_DATA_ARGS="--add-data $VLC_PLUGINS:vlc/plugins"
fi

pyinstaller \
    --onefile \
    --windowed \
    --name ytunes \
    --add-binary "$VLC_LIBDIR/libvlc.dylib:." \
    --add-binary "$VLC_LIBDIR/libvlccore.dylib:." \
    $VLC_DATA_ARGS \
    --collect-all PyQt6 \
    --hidden-import yt_dlp \
    --hidden-import vlc \
    --hidden-import requests \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --distpath build/pyinstaller \
    --workpath build/pyinstaller-work \
    --noconfirm \
    main.py

echo ""
echo "==> Done! Executable: build/pyinstaller/ytunes"
echo "    Size: $(du -h build/pyinstaller/ytunes | cut -f1)"
