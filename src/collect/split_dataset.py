"""Split annotated images into train/val/test sets."""

import argparse
import random
import shutil
from pathlib import Path


def split_dataset(
    images_dir: str,
    labels_dir: str,
    output_dir: str,
    train: float = 0.7,
    val: float = 0.2,
    seed: int = 42,
) -> None:
    random.seed(seed)
    images = sorted(Path(images_dir).glob("*.jpg")) + sorted(Path(images_dir).glob("*.png"))
    labeled = [img for img in images if (Path(labels_dir) / img.with_suffix(".txt").name).exists()]

    random.shuffle(labeled)
    n = len(labeled)
    n_train = int(n * train)
    n_val = int(n * val)

    splits = {
        "train": labeled[:n_train],
        "val": labeled[n_train : n_train + n_val],
        "test": labeled[n_train + n_val :],
    }

    for split, files in splits.items():
        img_out = Path(output_dir) / "images" / split
        lbl_out = Path(output_dir) / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)
        for img in files:
            shutil.copy(img, img_out / img.name)
            lbl = Path(labels_dir) / img.with_suffix(".txt").name
            shutil.copy(lbl, lbl_out / lbl.name)
        print(f"{split}: {len(files)} images")


def main():
    parser = argparse.ArgumentParser(description="Split dataset into train/val/test")
    parser.add_argument("--images", default="data/frames", help="Directory with images")
    parser.add_argument("--labels", default="data/annotations", help="Directory with YOLO labels")
    parser.add_argument("--output", default="data/dataset", help="Output dataset directory")
    parser.add_argument("--train", type=float, default=0.7)
    parser.add_argument("--val", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    split_dataset(args.images, args.labels, args.output, args.train, args.val, args.seed)


if __name__ == "__main__":
    main()
