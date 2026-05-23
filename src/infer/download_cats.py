"""Download real (non-AI) cat photos from The Cat API."""

import argparse
import json
import urllib.request
from pathlib import Path


def download_cats(output_dir: str, count: int, api_key: str = "") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    headers = {
        "x-api-key": api_key,
        "User-Agent": "sportsbook-meow/1.0",
    }
    saved = 0

    while saved < count:
        req = urllib.request.Request(
            "https://api.thecatapi.com/v1/images/search?mime_types=jpg,png&size=med",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())[0]

        url = data["url"]
        ext = url.rsplit(".", 1)[-1].split("?")[0]
        dest = out / f"cat_{saved + 1:03d}.{ext}"

        print(f"[{saved + 1}/{count}] {url}")
        img_req = urllib.request.Request(url, headers={"User-Agent": "sportsbook-meow/1.0"})
        with urllib.request.urlopen(img_req, timeout=15) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        saved += 1

    print(f"\nDownloaded {saved} cat images to {out}")


def main():
    parser = argparse.ArgumentParser(description="Download real cat photos from The Cat API")
    parser.add_argument("--output", default="src/infer/cats", help="Output directory")
    parser.add_argument("--count", type=int, default=20, help="Number of images to download")
    parser.add_argument("--api-key", default="", help="Optional Cat API key (higher rate limit)")
    args = parser.parse_args()
    download_cats(args.output, args.count, args.api_key)


if __name__ == "__main__":
    main()
