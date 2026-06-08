#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYINSTALLER="${PYINSTALLER:-pyinstaller}"
if [ -f "$PROJECT_DIR/venv/bin/pyinstaller" ]; then
    PYINSTALLER="$PROJECT_DIR/venv/bin/pyinstaller"
fi

echo "==> Building yTunes for Linux x86_64..."

rm -rf build/pyinstaller build/pyinstaller-work build/vlc-stage

# Auto-detect VLC library paths (different per distro)
VLC_LIB=""
VLC_CORE=""
VLC_PLUGINS=""

for dir in /usr/lib/x86_64-linux-gnu /usr/lib64 /usr/lib; do
    if [ -f "$dir/libvlc.so.5" ]; then
        VLC_LIB="$dir/libvlc.so.5"
        VLC_CORE="$dir/libvlccore.so.9"
    fi
    if [ -d "$dir/vlc/plugins" ]; then
        VLC_PLUGINS="$dir/vlc"
    fi
done

if [ -z "$VLC_LIB" ]; then
    echo "ERROR: libvlc.so.5 not found. Install VLC first."
    echo "  Debian/Ubuntu: sudo apt install vlc"
    echo "  Fedora:        sudo dnf install vlc"
    echo "  Arch:          sudo pacman -S vlc"
    exit 1
fi
if [ -z "$VLC_PLUGINS" ]; then
    echo "ERROR: VLC plugins not found."
    exit 1
fi

echo "    VLC lib:   $VLC_LIB"
echo "    VLC core:  $VLC_CORE"
echo "    VLC data:  $VLC_PLUGINS"

# Stage VLC without stale plugin cache
VLC_STAGE="build/vlc-stage"
mkdir -p "$VLC_STAGE"
cp -r "$VLC_PLUGINS"/* "$VLC_STAGE/"
rm -f "$VLC_STAGE/plugins/plugins.dat"

$PYINSTALLER \
    --onefile \
    --name ytunes \
    --add-data "build/vlc-stage:vlc" \
    --add-binary "$VLC_LIB:." \
    --add-binary "$VLC_CORE:." \
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
