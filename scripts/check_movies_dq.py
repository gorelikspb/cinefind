"""DQ on movies_clean (+ raw JSON present). Exit 1 if a check fails."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MOVIES = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"
TMDB_DIR = ROOT / "data" / "raw_private" / "tmdb" / "movies"

MIN_ROWS = 1
MIN_JOIN_RATIO = 0.9
MAX_EMPTY_OVERVIEW_RATIO = 0.2
MAX_EMPTY_GENRES_RATIO = 0.05


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"OK:   {msg}")


def main() -> int:
    errors: list[str] = []

    n_json = len(list(TMDB_DIR.glob("*.json"))) if TMDB_DIR.exists() else 0
    if n_json < 1:
        fail(f"no TMDb JSON files under {TMDB_DIR}", errors)
    else:
        ok(f"raw TMDb JSON files: {n_json}")

    if not MOVIES.exists():
        fail(f"missing {MOVIES} — run build_movies_clean.py first", errors)
        print(f"\n{len(errors)} check(s) failed")
        return 1

    df = pd.read_parquet(MOVIES)
    n = len(df)
    if n < MIN_ROWS:
        fail(f"row count {n} < MIN_ROWS {MIN_ROWS}", errors)
    else:
        ok(f"row count: {n}")

    required = ["tmdb_id", "title", "genres", "overview", "movielens_id"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        fail(f"missing columns: {missing_cols}", errors)
        print(f"\n{len(errors)} check(s) failed")
        return 1
    ok(f"required columns present: {required}")

    dup = int(df["tmdb_id"].duplicated().sum())
    if dup > 0:
        fail(f"duplicate tmdb_id rows: {dup}", errors)
    else:
        ok("no duplicate tmdb_id")

    joined = int(df["movielens_id"].notna().sum())
    join_ratio = joined / n if n else 0.0
    if join_ratio < MIN_JOIN_RATIO:
        fail(f"join coverage {join_ratio:.2%} ({joined}/{n}) < {MIN_JOIN_RATIO:.0%}", errors)
    else:
        ok(f"join coverage: {join_ratio:.2%} ({joined}/{n})")

    empty_overview = int((df["overview"].fillna("").astype(str).str.strip() == "").sum())
    empty_genres = int((df["genres"].fillna("").astype(str).str.strip() == "").sum())
    ov_ratio = empty_overview / n if n else 0.0
    ge_ratio = empty_genres / n if n else 0.0

    if ov_ratio > MAX_EMPTY_OVERVIEW_RATIO:
        fail(f"empty overview {ov_ratio:.2%} > {MAX_EMPTY_OVERVIEW_RATIO:.0%}", errors)
    else:
        ok(f"empty overview: {empty_overview}/{n}")

    if ge_ratio > MAX_EMPTY_GENRES_RATIO:
        fail(f"empty genres {ge_ratio:.2%} > {MAX_EMPTY_GENRES_RATIO:.0%}", errors)
    else:
        ok(f"empty genres: {empty_genres}/{n}")

    if errors:
        print(f"\n{len(errors)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
