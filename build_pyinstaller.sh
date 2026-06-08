#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Running Linux build script..."
exec "$SCRIPT_DIR/scripts/build-linux.sh" "$@"
