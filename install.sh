#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
SHARE_DIR="$HOME/.local/share/ytunes"

echo "Installing ytunes from $PROJECT_DIR..."

# --- Ensure virtual environment exists ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet PyQt6 python-vlc yt-dlp requests Pillow

# --- Install launcher to ~/.local/bin ---
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/ytunes" << 'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
SHARE_DIR="$HOME/.local/share/ytunes"
VENV_DIR="$SHARE_DIR/venv"
export VLC_PLUGIN_PATH="${VLC_PLUGIN_PATH:-/usr/lib/vlc/plugins}"
exec "$VENV_DIR/bin/python" "$SHARE_DIR/main.py" "$@"
LAUNCHER
chmod +x "$BIN_DIR/ytunes"
echo "  → Launcher: $BIN_DIR/ytunes"

# --- Install desktop entry ---
mkdir -p "$APP_DIR"
cp "$PROJECT_DIR/resources/ytunes.desktop" "$APP_DIR/ytunes.desktop"
echo "  → Desktop entry: $APP_DIR/ytunes.desktop"

# --- Install icon ---
mkdir -p "$ICON_DIR"
cp "$PROJECT_DIR/resources/ytunes.svg" "$ICON_DIR/ytunes.svg"
echo "  → Icon: $ICON_DIR/ytunes.svg"

# --- Update desktop database ---
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

# --- Copy project files to shared location ---
if [ ! -d "$SHARE_DIR" ] || [ "${1:-}" = "--force" ]; then
    echo "Copying project files to $SHARE_DIR..."
    mkdir -p "$SHARE_DIR"
    cp -r "$PROJECT_DIR/app"    "$SHARE_DIR/"
    cp -r "$PROJECT_DIR/core"   "$SHARE_DIR/"
    cp -r "$PROJECT_DIR/data"   "$SHARE_DIR/"
    cp -r "$PROJECT_DIR/utils"  "$SHARE_DIR/"
    cp -r "$PROJECT_DIR/resources" "$SHARE_DIR/"
    cp  "$PROJECT_DIR/main.py"  "$SHARE_DIR/"
    cp  "$PROJECT_DIR/requirements.txt" "$SHARE_DIR/"
    # Symlink venv to share dir
    ln -sfn "$VENV_DIR" "$SHARE_DIR/venv"
fi

echo ""
echo "Installation complete!"
echo "You can now launch ytunes from your application menu or by running: ytunes"
