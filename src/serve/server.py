"""
WebSocket inference server.

Accepts raw JPEG bytes from the browser extension, runs YOLO on the GPU,
and returns normalized bounding boxes as JSON.

Protocol:
  client → server : raw JPEG bytes
  server → client : {"detections": [{"x1":0.1,"y1":0.1,"x2":0.4,"y2":0.3,"conf":0.95}, ...]}
  server → client : {"error": "message"}   (on failure)
"""

import argparse
import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import websockets
import websockets.exceptions
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ── globals ──────────────────────────────────────────────────────────────────

_model: YOLO | None = None
_conf: float = 0.25
# Thread pool for JPEG decode + YOLO (YOLO releases the GIL for GPU work).
# One worker per GPU is enough; extra threads handle concurrent decode on the
# many available CPU cores.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="infer")

# Simple FPS counter
_frame_times: list[float] = []


# ── inference ─────────────────────────────────────────────────────────────────

def _infer(jpeg_bytes: bytes) -> list[dict]:
    """Decode JPEG, run YOLO, return normalised boxes. Runs in thread pool."""
    arr = np.frombuffer(jpeg_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    h, w = img.shape[:2]
    results = _model(img, conf=_conf, verbose=False)[0]

    detections = []
    for box in results.boxes:
        x1, y1, x2, y2 = map(float, box.xyxy[0])
        detections.append({
            "x1": x1 / w,
            "y1": y1 / h,
            "x2": x2 / w,
            "y2": y2 / h,
            "conf": round(float(box.conf[0]), 3),
        })
    return detections


# ── WebSocket handler ─────────────────────────────────────────────────────────

async def _handler(ws):
    addr = ws.remote_address
    log.info("connected  %s", addr)
    loop = asyncio.get_event_loop()

    try:
        async for message in ws:
            if not isinstance(message, bytes):
                await ws.send(json.dumps({"error": "send raw JPEG bytes"}))
                continue

            t0 = time.perf_counter()
            try:
                detections = await loop.run_in_executor(_executor, _infer, message)
            except Exception as exc:
                log.exception("inference error")
                await ws.send(json.dumps({"error": str(exc)}))
                continue

            elapsed = time.perf_counter() - t0
            _frame_times.append(elapsed)
            if len(_frame_times) > 100:
                _frame_times.pop(0)
            if len(_frame_times) % 50 == 0:
                avg_ms = sum(_frame_times) / len(_frame_times) * 1000
                log.info("avg inference %.1f ms  (%.0f fps)", avg_ms, 1000 / avg_ms)

            await ws.send(json.dumps({"detections": detections}))

    except websockets.exceptions.ConnectionClosed:
        pass

    log.info("disconnected %s", addr)


# ── entry point ───────────────────────────────────────────────────────────────

async def _serve(host: str, port: int):
    log.info("server ready  ws://%s:%d", host, port)
    async with websockets.serve(_handler, host, port, max_size=10 * 1024 * 1024):
        await asyncio.Future()  # run forever


def main():
    parser = argparse.ArgumentParser(description="sportsbook-meow inference server")
    parser.add_argument(
        "--weights",
        default="runs/detect/models/sportsbook_ads/weights/best.pt",  # updated by training automatically
        help="Path to trained .pt weights",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Detection confidence threshold")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    weights = Path(args.weights)
    if not weights.exists():
        # fall back to last.pt if best.pt isn't saved yet (mid-training)
        fallback = weights.parent / "last.pt"
        if fallback.exists():
            log.warning("best.pt not found, using last.pt")
            weights = fallback
        else:
            raise FileNotFoundError(f"No weights found at {args.weights}")

    global _model, _conf
    _conf = args.conf
    log.info("loading model: %s", weights)
    _model = YOLO(str(weights))
    # Warm up the GPU so the first real frame isn't slow
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    _model(dummy, verbose=False)
    log.info("GPU warmed up")

    asyncio.run(_serve(args.host, args.port))


if __name__ == "__main__":
    main()
