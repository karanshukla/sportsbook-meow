"""Detect sportsbook ads in video/images. Supports box, blur, or cat-replace modes."""
import argparse
import random
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

_CAT_POOL: list[np.ndarray] = []


def _load_cat_pool(cat_dir: str) -> list[np.ndarray]:
    global _CAT_POOL
    if _CAT_POOL:
        return _CAT_POOL

    path = Path(cat_dir)
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    files = [f for ext in exts for f in path.glob(ext)]

    if not files:
        raise FileNotFoundError(f"No cat images found in {cat_dir}")

    for f in files:
        img = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        if img.ndim == 2:                        # grayscale → BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:                  # BGRA → BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        _CAT_POOL.append(img)

    print(f"Loaded {len(_CAT_POOL)} cat images from {cat_dir}")
    return _CAT_POOL


def _apply_cat(frame: np.ndarray, boxes, cat_dir: str) -> np.ndarray:
    pool = _load_cat_pool(cat_dir)
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0:
            continue
        cat = random.choice(pool)
        frame[y1:y2, x1:x2] = cv2.resize(cat, (w, h))
    return frame


def _apply_blur(frame: np.ndarray, boxes, strength: int = 51) -> np.ndarray:
    k = strength if strength % 2 == 1 else strength + 1
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        roi = frame[y1:y2, x1:x2]
        if roi.size:
            frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)
    return frame


def process_video(model: YOLO, source: str, output: str, conf: float, mode: str, cat_dir: str, preview: bool = False) -> None:
    cap = cv2.VideoCapture(source)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    writer = cv2.VideoWriter(output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    processed = 0
    # Scale preview window down so it fits on screen
    preview_scale = min(1.0, 1280 / w)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, conf=conf, verbose=False)[0]
        if mode == "blur":
            frame = _apply_blur(frame, results.boxes)
        elif mode == "cat":
            frame = _apply_cat(frame, results.boxes, cat_dir)
        else:
            frame = results.plot()
        writer.write(frame)
        processed += 1
        if processed % 100 == 0:
            print(f"  {processed}/{total} frames", flush=True)

        if preview:
            small = cv2.resize(frame, (int(w * preview_scale), int(h * preview_scale)))
            cv2.imshow("sportsbook-meow", small)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Preview closed.")
                break

    cap.release()
    writer.release()
    if preview:
        cv2.destroyAllWindows()
    print(f"Saved to {output}")


def main():
    parser = argparse.ArgumentParser(description="Detect sportsbook ads in video")
    parser.add_argument("source", help="Video file path")
    parser.add_argument("--weights", default="runs/detect/models/sportsbook_ads/weights/best.pt")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--output", default="output.mp4")
    parser.add_argument(
        "--mode",
        choices=["box", "blur", "cat"],
        default="cat",
        help="box=draw boxes, blur=gaussian blur, cat=replace with random cat image",
    )
    parser.add_argument(
        "--cat-dir",
        default=str(Path(__file__).parent / "cats"),
        help="Directory of cat images to randomly pick from in cat mode",
    )
    parser.add_argument("--preview", action="store_true", help="Show live preview window (press Q to quit)")
    args = parser.parse_args()
    model = YOLO(args.weights)
    process_video(model, args.source, args.output, args.conf, args.mode, args.cat_dir, args.preview)


if __name__ == "__main__":
    main()
