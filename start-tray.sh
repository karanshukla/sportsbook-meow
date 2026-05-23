#!/usr/bin/env bash
# Launch the sportsbook-meow system-tray app inside the 'yolo' conda env.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

for candidate in \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" \
    "/opt/miniconda3/etc/profile.d/conda.sh"; do
    if [ -f "$candidate" ]; then
        # shellcheck source=/dev/null
        source "$candidate"
        break
    fi
done

if ! conda env list | awk '{print $1}' | grep -qx "yolo"; then
    echo "Error: conda env 'yolo' not found. Run ./install.sh first." >&2
    exit 1
fi

conda activate yolo

# WSL: ensure a DISPLAY is set so GTK/AppIndicator can find the desktop
if grep -qi microsoft /proc/version 2>/dev/null && [ -z "${DISPLAY:-}" ]; then
    export DISPLAY=:0
fi

exec python tray.py
