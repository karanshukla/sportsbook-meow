#!/usr/bin/env bash
# Launch the sportsbook-meow WebSocket inference server inside the 'yolo' env.
# All arguments are forwarded to server.py (--conf, --port, --host, --weights).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Locate and source conda so 'conda activate' works in non-interactive shells
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

# exec replaces this shell process so Ctrl-C / SIGTERM go straight to Python
exec python src/serve/server.py "$@"
