"""Extract frames from video files for annotation."""

import argparse
from pathlib import Path

import cv2


def extract_frames(video_path: str, output_dir: str, fps: int = 1) -> int:
    video = cv2.VideoCapture(video_path)
    video_fps = video.get(cv2.CAP_PROP_FPS)
    frame_interval = max(1, int(video_fps / fps))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(video_path).stem
    count = 0
    frame_idx = 0

    while True:
        ret, frame = video.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            cv2.imwrite(str(out_dir / f"{stem}_{frame_idx:06d}.jpg"), frame)
            count += 1
        frame_idx += 1

    video.release()
    print(f"Extracted {count} frames to {out_dir}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Extract frames from videos")
    parser.add_argument("video", help="Path to video file or directory of videos")
    parser.add_argument("--output", default="data/frames", help="Output directory")
    parser.add_argument("--fps", type=int, default=1, help="Frames per second to extract")
    args = parser.parse_args()

    input_path = Path(args.video)
    if input_path.is_dir():
        videos = (
            list(input_path.glob("*.mp4"))
            + list(input_path.glob("*.avi"))
            + list(input_path.glob("*.mkv"))
        )
        for v in videos:
            extract_frames(str(v), args.output, args.fps)
    else:
        extract_frames(str(input_path), args.output, args.fps)


if __name__ == "__main__":
    main()
