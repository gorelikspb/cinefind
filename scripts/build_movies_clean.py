"""TMDb JSON + MovieLens links → movies_clean (CSV + Parquet). DQ is a separate script."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TMDB_DIR = ROOT / "data" / "raw_private" / "tmdb" / "movies"
LINKS = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "links.csv"
MOVIES_ML = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "movies.csv"
OUT_DIR = ROOT / "data" / "raw_private" / "preview"
OUT_CSV = OUT_DIR / "movies_clean.csv"
OUT_PARQUET = OUT_DIR / "movies_clean.parquet"


def genres_str(data: dict) -> str:
    """TMDb genre list → 'Comedy|Drama'."""
    names = [g["name"] for g in data.get("genres") or [] if g.get("name")]
    return "|".join(names)


def keywords_str(data: dict) -> str:
    """TMDb keywords (from append_to_response) → pipe string."""
    kws = (data.get("keywords") or {}).get("keywords") or []
    names = [k["name"] for k in kws if k.get("name")]
    return "|".join(names)


def row_from_tmdb(data: dict) -> dict:
    """Flat columns we keep from one TMDb movie JSON."""
    return {
        "tmdb_id": data.get("id"),
        "imdb_id": data.get("imdb_id"),
        "title": data.get("title") or data.get("original_title"),
        "original_title": data.get("original_title"),
        "overview": data.get("overview") or "",
        "genres": genres_str(data),
        "keywords": keywords_str(data),
        "release_date": data.get("release_date") or "",
        "runtime": data.get("runtime"),
        "original_language": data.get("original_language"),
        "popularity": data.get("popularity"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
    }


def main() -> None:
    files = sorted(TMDB_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No TMDb JSON in {TMDB_DIR} — run fetch_tmdb_movies.py first")

    tmdb = pd.DataFrame(row_from_tmdb(json.loads(p.read_text(encoding="utf-8"))) for p in files)

    # MovieLens id bridge + their title/genres for comparison
    links = pd.read_csv(LINKS).dropna(subset=["tmdbId"]).copy()
    links["tmdbId"] = links["tmdbId"].astype(int)
    links = links.rename(
        columns={"movieId": "movielens_id", "tmdbId": "tmdb_id", "imdbId": "imdb_id_ml"}
    )
    ml_movies = pd.read_csv(MOVIES_ML).rename(
        columns={"movieId": "movielens_id", "title": "title_ml", "genres": "genres_ml"}
    )

    out = tmdb.merge(links[["movielens_id", "tmdb_id"]], on="tmdb_id", how="left")
    out = out.merge(ml_movies, on="movielens_id", how="left")

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
