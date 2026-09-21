"""TMDb JSON + MovieLens links → movies_clean (CSV + Parquet). Local disk I/O."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from movies_clean_lib import build_movies_clean

ROOT = Path(__file__).resolve().parents[1]
TMDB_DIR = ROOT / "data" / "raw_private" / "tmdb" / "movies"
LINKS = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "links.csv"
MOVIES_ML = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "movies.csv"
OUT_DIR = ROOT / "data" / "raw_private" / "preview"
OUT_CSV = OUT_DIR / "movies_clean.csv"
OUT_PARQUET = OUT_DIR / "movies_clean.parquet"


def main() -> None:
    files = sorted(TMDB_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No TMDb JSON in {TMDB_DIR} — run fetch_tmdb_movies.py first")

    rows = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    out = build_movies_clean(rows, pd.read_csv(LINKS), pd.read_csv(MOVIES_ML))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    out.to_parquet(OUT_PARQUET, index=False)

    matched = int(out["movielens_id"].notna().sum())
    print(f"movies: {len(out)}")
    print(f"joined to MovieLens: {matched}/{len(out)}")
    print(f"wrote {OUT_CSV.name}, {OUT_PARQUET.name}")
    print(out[["tmdb_id", "title", "genres", "movielens_id"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
