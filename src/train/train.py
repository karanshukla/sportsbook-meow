"""Train YOLO model on sportsbook ad dataset."""

import argparse
from pathlib import Path

from ultralytics import YOLO


def train(config: str, resume: bool = False, weights: str | None = None) -> None:
    import yaml

    with open(config) as f:
        cfg = yaml.safe_load(f)

    model_path = weights or cfg.pop("model", "yolov8s.pt")
    model = YOLO(model_path)

    if resume:
        model.train(resume=True)
    else:
        model.train(**cfg)

    print(
        f"Training complete. Best weights: "
        f"{Path(cfg.get('project', 'models')) / cfg.get('name', 'train') / 'weights/best.pt'}"
    )


def main():
    parser = argparse.ArgumentParser(description="Train YOLO on sportsbook ads")
    parser.add_argument("--config", default="configs/train.yaml", help="Training config path")
    parser.add_argument("--weights", help="Override starting weights (e.g. yolov8n.pt, yolov8m.pt)")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted training")
    args = parser.parse_args()
    train(args.config, args.resume, args.weights)


if __name__ == "__main__":
    main()
