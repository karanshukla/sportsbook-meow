# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Fine-tune a YOLOv8 model to detect sportsbook betting ads (logos, banners, overlays) in sports broadcast video, then blur or remove them in real time.

## Environment setup

```bash
conda create -n yolo python=3.11 -y && conda activate yolo
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126  # RTX 5070 (Blackwell) requires cu126+
pip install -r requirements.txt
```

Verify GPU: `python -c "import torch; print(torch.cuda.is_available())"`

## Key commands

```bash
# Extract frames from raw videos (1 fps)
python src/collect/extract_frames.py data/raw/ --fps 1

# Split annotated frames into train/val/test
python src/collect/split_dataset.py --images data/frames --labels data/annotations

# Train
python src/train/train.py --config configs/train.yaml

# Resume interrupted training
python src/train/train.py --config configs/train.yaml --resume

# Detect and blur ads in a video
python src/infer/detect.py match.mp4 --blur --output clean.mp4

# Detect with bounding boxes (no blur)
python src/infer/detect.py match.mp4 --output annotated.mp4
```

## Architecture

The pipeline has three stages:

**1. Data preparation** (`src/collect/`)
- `extract_frames.py` — reads video files with OpenCV, samples at a configurable fps, writes JPGs to `data/frames/`
- `split_dataset.py` — takes annotated images + YOLO `.txt` label files, shuffles deterministically, copies into `data/dataset/{images,labels}/{train,val,test}/`

**2. Training** (`src/train/train.py`)
- Thin wrapper around `ultralytics.YOLO`. Reads `configs/train.yaml` for all hyperparameters, then calls `model.train(**cfg)`. Output weights land in `models/sportsbook_ads/weights/`.

**3. Inference** (`src/infer/detect.py`)
- Loads a `.pt` weights file, runs frame-by-frame on video via OpenCV, either blurs detected regions (`GaussianBlur`) or calls `results.plot()` to draw boxes, writes output video.

## Configs

- `data.yaml` — YOLO dataset manifest at the repo root; absolute `path:` key + relative split paths. This is what Ultralytics reads during training.
- `configs/train.yaml` — all Ultralytics training kwargs plus a `model:` key for the starting checkpoint. Increasing `batch` or `imgsz` is the first lever to pull for better results.

## Classes

| ID | Name   |
|----|--------|
| 0  | logo   |

One class only — sportsbook brand logos. Add new classes by appending to `names` in `data.yaml` and incrementing `nc`.

## Data & model files

Large files are gitignored: `data/raw/`, `data/frames/`, `data/dataset/`, `models/`, `*.pt`. Use external storage (DVC, S3, Roboflow) for datasets and weights.

## Annotation

Use [LabelImg](https://github.com/HumanSignal/labelImg) or [Roboflow](https://roboflow.com) to annotate frames in YOLO format (one `.txt` per image, same stem). Output label files go in `data/annotations/` before running `split_dataset.py`.
