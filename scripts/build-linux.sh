#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYINSTALLER="${PYINSTALLER:-pyinstaller}"
# Prefer venv if it exists
if [ -f "$PROJECT_DIR/venv/bin/pyinstaller" ]; then
    PYINSTALLER="$PROJECT_DIR/venv/bin/pyinstaller"
fi

echo "==> Building yTunes for Linux x86_64..."

rm -rf build/pyinstaller build/pyinstaller-work build/vlc-stage

# Stage VLC without stale plugin cache
VLC_STAGE="build/vlc-stage"
mkdir -p "$VLC_STAGE"
cp -r /usr/lib/vlc/* "$VLC_STAGE/"
rm -f "$VLC_STAGE/plugins/plugins.dat"

$PYINSTALLER \
    --onefile \
    --name ytunes \
    --add-data "build/vlc-stage:vlc" \
    --add-binary "/usr/lib/libvlc.so.5:." \
    --add-binary "/usr/lib/libvlccore.so.9:." \
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

rm -rf build/vlc-stage

echo ""
echo "==> Done! Executable: build/pyinstaller/ytunes"
echo "    Size: $(du -h build/pyinstaller/ytunes | cut -f1)"
