# sportsbook-meow 🐱

Real-time replacement of sportsbook betting ads in sports video — local files and live web streams — with cats. Uses a YOLOv8s model fine-tuned to detect betting logos in broadcast footage.

> **Pre-trained weights** — download `best.pt` from the [latest GitHub Release](../../releases/latest) to skip training entirely.

> **Disclaimer** — For personal use only. Not affiliated with any sportsbook brand. Model weights are learned parameters for the purpose of ad detection and replacement; no third-party brand assets are distributed with this project. This project MAY NOT work with DRM enabled Streams (Widevine). This application is only for research, educational or private use. This application does NOT block ads via host file manipulation. Running ML inferencing locally is demanding, so you may run into bugs, lag or freezes with your system, depending on your hardware.

---

## How it works

```
Video frame → YOLO detection → bounding boxes → paste random cat photo over each ad
```

The model detects one class: `logo` (sportsbook brand logos). Every detected region is replaced with a randomly chosen real cat photo from a local pool.

**Full pipeline (browser extension + local server):**

```
Web stream (YouTube / Twitch / DAZN etc.)
        ↓
Browser extension captures <video> frames
        ↓
Local WebSocket inference server (YOLO on GPU)
        ↓
Extension overlays cats on detected regions in real time
```

---

## Project status

| Component | Status |
|-----------|--------|
| YOLO model training | ✅ Done — mAP50 0.94+ |
| Extended brand coverage (Betway, Sportsbet, Canadian) | ✅ Done — fine-tuned on expanded dataset |
| Offline video processing (cat replace / blur / box) | ✅ Done |
| Cat image downloader (real photos, no AI) | ✅ Done |
| Local WebSocket inference server | ✅ Done |
| Browser extension (Chrome / Edge / Firefox) | ✅ Done |
| Real-time local video player | 🔲 Planned |

---

## Setup

### Windows (WSL2) — recommended for NVIDIA GPU

1. **Enable WSL2** (PowerShell as admin, then reboot):
   ```powershell
   wsl --install
   ```

2. **NVIDIA drivers** — install the Windows driver from [nvidia.com/drivers](https://www.nvidia.com/drivers). Do **not** install drivers inside WSL2; it inherits them from Windows automatically.

3. **Verify GPU inside WSL2:**
   ```bash
   nvidia-smi
   ```

4. Continue with the Linux steps below inside WSL2.

### Linux / WSL2

```bash
# Install Miniconda if not already present
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh && source ~/.bashrc

conda create -n yolo python=3.11 -y
conda activate yolo

# Choose the right CUDA version for your GPU:
#   RTX 5000 series (Blackwell, sm_120) → nightly cu128
#   RTX 4000 / 3000 series             → stable cu121
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128

pip install -r requirements.txt
```

Verify: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`

### macOS (CPU / Apple Silicon MPS)

```bash
conda create -n yolo python=3.11 -y && conda activate yolo
pip install torch torchvision   # uses MPS on Apple Silicon automatically
pip install -r requirements.txt
```

---

## Quick start (pre-trained model)

### 1. Download cat images

Get a free API key from [thecatapi.com](https://thecatapi.com) for higher rate limits, then:

```bash
conda activate yolo

# First time: copy the example env file and add your key
cp .env.example .env
# Edit .env and set CAT_API_KEY=your_key_here

# Download 30 real cat photos
python src/infer/download_cats.py --count 30 --api-key $(grep CAT_API_KEY .env | cut -d= -f2)
```

No API key? It still works without one (lower rate limit):
```bash
python src/infer/download_cats.py --count 30
```

### 2. Prepare cats for the browser extension

```bash
python src/infer/prepare_extension_cats.py
# resizes and copies cats → extension/cats/
```

### 3. Start the inference server

```bash
conda activate yolo
python src/serve/server.py
# GPU warms up, then listens on ws://localhost:8765
```

### 4. Load the browser extension

- **Chrome / Edge:** go to `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select the `extension/` folder
- **Firefox:** go to `about:debugging` → **This Firefox** → **Load Temporary Add-on** → select `extension/manifest.json`

Click the 🐱 icon in your toolbar — the popup shows the server connection status and an on/off toggle.

> **Chrome permission prompt** — the first time the extension tries to connect, Chrome will show a banner asking permission to access `localhost`. Click **Allow**. You only need to do this once. If you miss it, go to `chrome://extensions` → sportsbook-meow → **Site access** and allow localhost manually.

### 5. Watch sport, enjoy cats

Open any stream on YouTube, Twitch etc. Betting logos are replaced with random cats in real time.

---

## Training your own model

### 1. Get the dataset

Annotate your own frames using [LabelImg](https://github.com/HumanSignal/labelImg) or [Roboflow](https://roboflow.com) in YOLO format, one class: `logo`. Place images in `train/images/` and labels in `train/labels/`, then create a `valid/` split the same way.

To download a Roboflow dataset export (YOLOv8 format) and split it:

```bash
conda activate yolo
curl -sL "https://app.roboflow.com/ds/YOURKEY" -o roboflow.zip
python - <<'EOF'
import zipfile, random, shutil
from pathlib import Path
zipfile.ZipFile("roboflow.zip").extractall(".")
Path("roboflow.zip").unlink()
random.seed(42)
imgs = sorted(Path("train/images").glob("*.jpg"))
random.shuffle(imgs)
val = imgs[:int(len(imgs) * 0.2)]
for d in ["valid/images", "valid/labels"]:
    Path(d).mkdir(parents=True, exist_ok=True)
for img in val:
    lbl = Path("train/labels") / img.with_suffix(".txt").name
    shutil.move(str(img), f"valid/images/{img.name}")
    if lbl.exists():
        shutil.move(str(lbl), f"valid/labels/{lbl.name}")
print(f"Train: {len(list(Path('train/images').glob('*.jpg')))}  Val: {len(list(Path('valid/images').glob('*.jpg')))}")
EOF
```

### 2. Train

```bash
conda activate yolo
python src/train/train.py --config configs/train.yaml
```

Weights are saved to `runs/detect/models/sportsbook_ads/weights/best.pt`. Training 100 epochs on an RTX 5070 takes roughly 2–3 hours.

> **Fresh clone:** `configs/train.yaml` defaults to fine-tuning from `best.pt`. For a first run from scratch, either download `best.pt` from the [latest release](../../releases/latest) or change `model:` in `configs/train.yaml` to `yolov8s.pt`.

To resume an interrupted run:
```bash
python src/train/train.py --config configs/train.yaml --resume
```

### 3. Upload weights to GitHub Releases

```bash
gh release create v1.0 runs/detect/models/sportsbook_ads/weights/best.pt \
  --title "sportsbook-meow v1.0" \
  --notes "YOLOv8s fine-tuned for sportsbook logo detection in broadcast video"
```

---

## Running inference on a local video

```bash
conda activate yolo

# Replace ads with random cats and watch live (press Q to stop preview)
python src/infer/detect.py match.mp4 --mode cat --output clean.mp4 --preview

# Save only, no preview window
python src/infer/detect.py match.mp4 --output clean.mp4

# Blur ads instead
python src/infer/detect.py match.mp4 --mode blur --output clean.mp4

# Draw bounding boxes only (useful for checking model quality)
python src/infer/detect.py match.mp4 --mode box --output annotated.mp4 --preview

# Custom weights or confidence threshold
python src/infer/detect.py match.mp4 --weights path/to/best.pt --conf 0.35

# Use a custom cat image folder
python src/infer/detect.py match.mp4 --cat-dir ~/my-cats/
```

---

## Project structure

```
├── data.yaml                              # YOLO dataset config
├── configs/train.yaml                     # Training hyperparameters
├── train/ valid/                          # Dataset splits (gitignored)
├── runs/detect/models/sportsbook_ads/     # Training output + weights (gitignored)
├── extension/                             # Browser extension (Chrome/Edge/Firefox)
│   ├── manifest.json
│   ├── content.js                         # Hooks <video> elements, overlays cats
│   ├── background.js                      # Stores settings
│   ├── popup/                             # Toolbar popup (toggle + server URL)
│   └── cats/                             # Cat images bundled with extension (gitignored)
└── src/
    ├── collect/
    │   ├── extract_frames.py              # Extract frames from raw video
    │   ├── split_dataset.py              # Train/val/test splitter
    │   └── download_logos.py             # Bulk-download brand logos via Bing (icrawler)
    ├── train/train.py                     # Training entrypoint
    ├── infer/
    │   ├── detect.py                      # Offline video: cat / blur / box
    │   ├── download_cats.py               # Fetch real cat photos from The Cat API
    │   ├── prepare_extension_cats.py      # Resize cats for extension bundle
    │   └── cats/                          # Cat image pool (gitignored)
    └── serve/
        └── server.py                      # WebSocket inference server (ws://localhost:8765)
```
