#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="$SCRIPT_DIR/venv/bin:$PATH"
PYTHON="$SCRIPT_DIR/venv/bin/python"
NUITKA="$PYTHON -m nuitka"

echo "==> Building yTunes executable with Nuitka..."

$NUITKA \
    --standalone \
    --onefile \
    --enable-plugin=pyqt6 \
    --include-package=PyQt6 \
    --include-package=yt_dlp \
    --include-package=requests \
    --include-package=vlc \
    --include-data-dir=/usr/lib/vlc=vlc \
    --include-data-file=/usr/lib/libvlc.so.5=libvlc.so.5 \
    --include-data-file=/usr/lib/libvlccore.so.9=libvlccore.so.9 \
    --output-dir=build \
    --output-filename=ytunes \
    main.py

echo ""
echo "==> Done! Executable at: build/ytunes"
echo "    Size: $(du -h build/ytunes | cut -f1)"
