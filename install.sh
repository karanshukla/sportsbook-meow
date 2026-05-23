#!/usr/bin/env bash
# One-shot setup for the sportsbook-meow inference server.
# Works on WSL, Linux, and macOS (Apple Silicon + Intel).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# ── 1. Detect platform ────────────────────────────────────────────────────────

OS=$(uname -s)   # Linux | Darwin
ARCH=$(uname -m) # x86_64 | arm64

IS_WSL=false
if [ "$OS" = "Linux" ] && grep -qi microsoft /proc/version 2>/dev/null; then
    IS_WSL=true
fi

echo "==> Platform: $OS/$ARCH$([ "$IS_WSL" = true ] && echo ' (WSL)' || true)"

# ── 2. Ensure conda is available ──────────────────────────────────────────────

_find_conda_sh() {
    for candidate in \
        "$HOME/miniconda3/etc/profile.d/conda.sh" \
        "$HOME/anaconda3/etc/profile.d/conda.sh" \
        "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" \
        "/opt/miniconda3/etc/profile.d/conda.sh"; do
        [ -f "$candidate" ] && echo "$candidate" && return 0
    done
    return 1
}

if ! command -v conda &>/dev/null; then
    CONDA_SH=$(_find_conda_sh || true)
    if [ -n "$CONDA_SH" ]; then
        # shellcheck source=/dev/null
        source "$CONDA_SH"
    else
        echo "==> conda not found — installing Miniconda..."
        if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
            MINI_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        elif [ "$OS" = "Darwin" ]; then
            MINI_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        else
            MINI_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        fi
        curl -fsSL "$MINI_URL" -o /tmp/miniconda_install.sh
        bash /tmp/miniconda_install.sh -b -p "$HOME/miniconda3"
        rm /tmp/miniconda_install.sh
        # shellcheck source=/dev/null
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda init bash
        echo ""
        echo "  Miniconda installed. Open a new terminal and re-run:"
        echo "    ./install.sh"
        exit 0
    fi
fi

# Make sure conda shell functions are loaded in this session
CONDA_SH=$(_find_conda_sh || true)
[ -n "$CONDA_SH" ] && source "$CONDA_SH" || true

# ── 3. Create / reuse the conda environment ───────────────────────────────────

if conda env list | awk '{print $1}' | grep -qx "yolo"; then
    echo "==> conda env 'yolo' already exists — skipping creation"
else
    echo "==> Creating conda env 'yolo' (Python 3.11)..."
    conda create -n yolo python=3.11 -y
fi

# ── 4. Install PyTorch with the right backend ─────────────────────────────────

echo "==> Installing PyTorch..."
if [ "$OS" = "Darwin" ]; then
    # macOS: CPU + Metal (MPS) — no CUDA
    conda run -n yolo pip install --quiet torch torchvision
elif nvidia-smi &>/dev/null; then
    # Linux / WSL with an NVIDIA GPU — RTX 5070 (Blackwell) needs cu126+
    conda run -n yolo pip install --quiet torch torchvision \
        --index-url https://download.pytorch.org/whl/cu126
else
    echo "  (no NVIDIA GPU detected — installing CPU-only PyTorch)"
    conda run -n yolo pip install --quiet torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu
fi

# ── 5. Install project requirements ──────────────────────────────────────────

echo "==> Installing requirements..."
conda run -n yolo pip install --quiet -r requirements.txt

# ── 6. Verify GPU ─────────────────────────────────────────────────────────────

echo "==> Checking GPU access..."
conda run -n yolo python - <<'EOF'
import torch
if torch.cuda.is_available():
    print(f"  CUDA GPU: {torch.cuda.get_device_name(0)}")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    print("  Apple MPS (Metal) available")
else:
    print("  No GPU found — running on CPU (inference will be slow)")
EOF

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "Installation complete."
echo ""
echo "  Start the server:       ./start-server.sh"
echo "  Custom conf threshold:  ./start-server.sh --conf 0.35"
echo "  Custom port:            ./start-server.sh --port 9000"
echo ""
echo "  Weights must exist at:  models/sportsbook_ads/weights/best.pt"
echo "  Train first with:       make train   (or python src/train/train.py)"
