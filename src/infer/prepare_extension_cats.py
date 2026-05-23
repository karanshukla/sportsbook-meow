"""
Resize cat images from src/infer/cats/ and copy them to extension/cats/.

Run this after download_cats.py to bundle cats with the browser extension.
Images are resized to at most 300×300 px to keep the extension package small.
"""

import argparse
import shutil
from pathlib import Path

import cv2


def prepare(src_dir: str, dst_dir: str, max_dim: int, count: int) -> None:
    src = Path(src_dir)
    dst = Path(dst_dir)
    dst.mkdir(parents=True, exist_ok=True)

    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    files = sorted(f for ext in exts for f in src.glob(ext))[:count]

    if not files:
        print(f"No images found in {src}. Run download_cats.py first.")
        return

    for i, f in enumerate(files, 1):
        img = cv2.imread(str(f))
        if img is None:
            continue
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        dest = dst / f"cat_{i:03d}.jpg"
        cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 85])

    print(f"Copied {len(files)} cat images → {dst}")


def main():
    parser = argparse.ArgumentParser(description="Prepare cat images for browser extension")
    parser.add_argument("--src", default="src/infer/cats", help="Source cat image directory")
    parser.add_argument("--dst", default="extension/cats", help="Extension cats directory")
    parser.add_argument("--max-dim", type=int, default=300, help="Max image dimension in pixels")
    parser.add_argument("--count", type=int, default=30, help="Max images to include")
    args = parser.parse_args()
    prepare(args.src, args.dst, args.max_dim, args.count)


if __name__ == "__main__":
    main()
