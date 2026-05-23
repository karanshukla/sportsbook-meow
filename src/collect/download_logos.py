"""
Download sportsbook logo images from Bing for training data.

Usage:
    python src/collect/download_logos.py --output data/raw_logos --per-brand 10
    python src/collect/download_logos.py --output data/raw_logos --per-brand 5 \
        --brands betmgm draftkings caesars unibet

Requires: pip install icrawler
"""

import argparse
import re
import shutil
from pathlib import Path

CANADIAN_SPORTSBOOKS = {
    "betmgm": [
        "BetMGM Canada logo",
        "BetMGM sportsbook logo",
        "BetMGM lion logo",
    ],
    "draftkings": [
        "DraftKings Canada logo",
        "DraftKings sportsbook logo",
        "DraftKings crown logo",
    ],
    "fanduel": [
        "FanDuel Canada logo",
        "FanDuel sportsbook logo",
        "FanDuel sports betting logo",
    ],
    "bet365": [
        "bet365 Canada logo",
        "bet365 sportsbook logo",
        "bet365 green logo",
    ],
    "pointsbet": [
        "PointsBet Canada logo",
        "PointsBet sportsbook logo",
        "PointsBet sports betting logo",
    ],
    "betway": [
        "Betway Canada logo",
        "Betway sportsbook logo",
        "Betway sports betting logo",
    ],
    "betrivers": [
        "BetRivers Canada logo",
        "BetRivers sportsbook logo",
        "BetRivers sports betting logo",
    ],
    "thescore_bet": [
        "theScore Bet Canada logo",
        "theScore Bet sportsbook logo",
        "theScore Bet logo",
    ],
    "sports_interaction": [
        "Sports Interaction logo",
        "SIA sportsbook logo Canada",
        "Sports Interaction Canada betting logo",
    ],
    "proline": [
        "Proline+ OLG logo",
        "Proline Plus Ontario sportsbook logo",
        "OLG Proline logo",
    ],
    # Ontario iGO-regulated, launched 2022+
    "caesars": [
        "Caesars Sportsbook Ontario logo",
        "Caesars Sportsbook Canada logo",
        "Caesars sports betting logo",
    ],
    "unibet": [
        "Unibet Ontario logo",
        "Unibet Canada sportsbook logo",
        "Unibet sports betting logo",
    ],
    "betano": [
        "Betano Ontario logo",
        "Betano Canada sportsbook logo",
        "Betano sports betting logo",
    ],
    "hard_rock_bet": [
        "Hard Rock Bet Ontario logo",
        "Hard Rock Bet sportsbook logo",
        "Hard Rock Bet Canada logo",
    ],
    "888sport": [
        "888sport Ontario logo",
        "888sport Canada sportsbook logo",
        "888sport logo",
    ],
    "leovegas": [
        "LeoVegas Sports Ontario logo",
        "LeoVegas Canada sportsbook logo",
        "LeoVegas sports betting logo",
    ],
    "bet99": [
        "BET99 Canada logo",
        "BET99 sportsbook logo",
        "BET99 sports betting logo",
    ],
    "tonybet": [
        "TonyBet Ontario logo",
        "TonyBet Canada sportsbook logo",
        "TonyBet sports betting logo",
    ],
    "tooniebet": [
        "ToonieBet Ontario logo",
        "ToonieBet Canada sportsbook logo",
        "ToonieBet sports betting logo",
    ],
    "betvictor": [
        "BetVictor Ontario logo",
        "BetVictor Canada sportsbook logo",
        "BetVictor sports betting logo",
    ],
    "tipico": [
        "Tipico Ontario logo",
        "Tipico Canada sportsbook logo",
        "Tipico sports betting logo",
    ],
    "casumo": [
        "Casumo Sports Ontario logo",
        "Casumo Canada sportsbook logo",
        "Casumo sports betting logo",
    ],
    # Canadian-founded / offshore popular in Canada
    "bodog": [
        "Bodog Canada logo",
        "Bodog sportsbook logo",
        "Bodog sports betting logo",
    ],
    "rivalry": [
        "Rivalry sportsbook logo",
        "Rivalry Canada esports betting logo",
        "Rivalry bet logo",
    ],
    "northstar_bets": [
        "NorthStar Bets Ontario logo",
        "NorthStar Bets sportsbook logo",
        "NorthStar Bets Canada logo",
    ],
    "pinnacle": [
        "Pinnacle Sports logo",
        "Pinnacle sportsbook logo Canada",
        "Pinnacle betting logo",
    ],
    # Provincial lottery / crown corp sportsbooks
    "playnow": [
        "PlayNow BC sportsbook logo",
        "BCLC PlayNow sports betting logo",
        "PlayNow British Columbia logo",
    ],
    "mise_o_jeu": [
        "Mise-o-jeu Quebec logo",
        "Loto-Quebec sports betting logo",
        "Mise-o-jeu sportsbook logo",
    ],
    "atlantic_lottery": [
        "Atlantic Lottery sports betting logo",
        "ALC sportsbook logo Canada",
        "Atlantic Lottery Corporation logo",
    ],
}


def _sanitize(filename: str) -> str:
    return re.sub(r"[^\w\-.]", "_", filename)


def download_logos(
    output_dir: str,
    per_brand: int = 10,
    brands: list[str] | None = None,
) -> None:
    try:
        from icrawler.builtin import BingImageCrawler
    except ImportError:
        raise SystemExit("icrawler is not installed. Run: pip install icrawler") from None

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    targets = (
        {k: CANADIAN_SPORTSBOOKS[k] for k in brands if k in CANADIAN_SPORTSBOOKS}
        if brands
        else CANADIAN_SPORTSBOOKS
    )

    total = 0
    for brand, queries in targets.items():
        brand_dir = out / brand
        brand_dir.mkdir(exist_ok=True)

        # Spread per_brand images across all search queries for variety
        per_query = max(1, per_brand // len(queries))
        remainder = per_brand - per_query * len(queries)

        for i, query in enumerate(queries):
            # Give the remainder to the first query
            count = per_query + (remainder if i == 0 else 0)
            query_dir = brand_dir / f"q{i}"
            query_dir.mkdir(exist_ok=True)

            print(f"\n[{brand}] '{query}' → {count} images")
            crawler = BingImageCrawler(
                storage={"root_dir": str(query_dir)},
                downloader_threads=4,
            )
            crawler.crawl(
                keyword=query,
                max_num=count,
                filters={"type": "photo"},
            )

        # Flatten all query subdirs into brand_dir with sequential names
        idx = 1
        for query_dir in sorted(brand_dir.glob("q*")):
            for img in sorted(query_dir.iterdir()):
                if img.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    dest = brand_dir / f"{brand}_{idx:04d}{img.suffix.lower()}"
                    shutil.move(str(img), dest)
                    idx += 1
            query_dir.rmdir()

        saved = idx - 1
        total += saved
        print(f"  -> {saved} images saved to {brand_dir}")

    print(f"\nDone. {total} total images in {out}")
    print(
        "\nNext step: annotate with LabelImg or Roboflow, then run:\n"
        "  python src/collect/split_dataset.py "
        f"--images {out} --labels data/annotations"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Bulk-download Canadian sportsbook logos for YOLO training"
    )
    parser.add_argument("--output", default="data/raw_logos", help="Root output directory")
    parser.add_argument(
        "--per-brand",
        type=int,
        default=10,
        help="Images to download per brand (default 10; use 10 brands → 100 total)",
    )
    parser.add_argument(
        "--brands",
        nargs="+",
        choices=list(CANADIAN_SPORTSBOOKS.keys()),
        help="Subset of brands to download (default: all)",
    )
    args = parser.parse_args()
    download_logos(args.output, args.per_brand, args.brands)


if __name__ == "__main__":
    main()
