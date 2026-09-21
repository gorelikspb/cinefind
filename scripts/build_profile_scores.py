"""Gold: one row per demo-profile × candidate with score channels.

Channels (plug-ins — none is “the” production brain):
  content_score, mood_score, collab_n, collab_avg, ml_score, hf_score

  python scripts/build_profile_scores.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collab_lib import (
    collab_candidate_scores,
    find_neighbor_user_ids,
    load_links,
    load_ratings,
    tmdb_ids_to_movie_ids,
)
from ml_lib import MODEL_PATH, load_cf_svd, ml_scores_for_seeds
from scoring_lib import DEMO_PROFILES, OUT_DIR, load_movies, mood_score, score_row, split_pipe

OUT_PARQUET = OUT_DIR / "profile_scores.parquet"
OUT_CSV = OUT_DIR / "profile_scores.csv"


def content_channels(movies: pd.DataFrame, seed_tmdb_ids: tuple[int, ...], mood: str) -> pd.DataFrame:
    seeds = movies[movies["tmdb_id"].isin(seed_tmdb_ids)]
    seed_genres: set[str] = set()
    seed_keywords: set[str] = set()
    for _, row in seeds.iterrows():
        seed_genres |= split_pipe(row.get("genres"))
        seed_keywords |= split_pipe(row.get("keywords"))

    rows = []
    for _, row in movies[~movies["tmdb_id"].isin(seed_tmdb_ids)].iterrows():
        score, reason = score_row(row, seed_genres, seed_keywords)
        ms = mood_score(row, mood)
        if ms:
            reason = f"{reason}; mood:{mood}" if reason != "weak match" else f"mood:{mood}"
        rows.append(
            {
                "tmdb_id": int(row["tmdb_id"]),
                "title": row["title"],
                "genres": row.get("genres"),
                "poster_path": row.get("poster_path"),
                "overview": row.get("overview") or "",
                "content_score": float(score),
                "mood_score": float(ms),
                "content_reason": reason,
            }
        )
    return pd.DataFrame(rows)


def collab_channels(
    movies: pd.DataFrame,
    seed_tmdb_ids: tuple[int, ...],
    links: pd.DataFrame,
    ratings: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    seed_movie_ids = tmdb_ids_to_movie_ids(seed_tmdb_ids, links)
    neighbors = find_neighbor_user_ids(ratings, seed_movie_ids)
    tmdb_to_ml = dict(zip(links["tmdb_id"], links["movieId"]))
    ml_to_tmdb = dict(zip(links["movieId"], links["tmdb_id"]))
    seed_set = {int(x) for x in seed_tmdb_ids}

    allowed = {
        int(tmdb_to_ml[tid])
        for tid in movies["tmdb_id"].astype(int)
        if tid not in seed_set and tid in tmdb_to_ml
    }
    base = {
        tid: {"tmdb_id": tid, "collab_n": 0, "collab_avg": 0.0}
        for tid in movies["tmdb_id"].astype(int)
        if tid not in seed_set
    }
    agg = collab_candidate_scores(ratings, neighbors, seed_movie_ids, allowed)
    for _, row in agg.iterrows():
        tid = ml_to_tmdb.get(int(row["movieId"]))
        if tid in base:
            base[tid]["collab_n"] = int(row["n_likers"])
            base[tid]["collab_avg"] = float(row["avg_rating"])
    return pd.DataFrame(list(base.values())), len(neighbors)


def ml_channel(
    movies: pd.DataFrame,
    seed_tmdb_ids: tuple[int, ...],
    links: pd.DataFrame,
) -> pd.DataFrame:
    """sklearn SVD; zeros if pkl missing."""
    seed_set = {int(x) for x in seed_tmdb_ids}
    zeros = pd.DataFrame(
        {"tmdb_id": [int(t) for t in movies["tmdb_id"] if int(t) not in seed_set], "ml_score": 0.0}
    )
    if not MODEL_PATH.exists():
        print("no cf_svd.pkl — ml_score=0 (run train_cf_svd.py)")
        return zeros

    model = load_cf_svd()
    tmdb_to_ml = dict(zip(links["tmdb_id"], links["movieId"]))
    ml_to_tmdb = dict(zip(links["movieId"], links["tmdb_id"]))
    seed_ml = tmdb_ids_to_movie_ids(seed_tmdb_ids, links)
    allowed = {
        int(tmdb_to_ml[tid])
        for tid in movies["tmdb_id"].astype(int)
        if tid not in seed_set and tid in tmdb_to_ml
    }
    ml_df = ml_scores_for_seeds(seed_ml, allowed, model=model)
    if ml_df.empty:
        return zeros
    ml_df["tmdb_id"] = ml_df["movieId"].map(ml_to_tmdb)
    ml_df = ml_df.dropna(subset=["tmdb_id"])
    ml_df["tmdb_id"] = ml_df["tmdb_id"].astype(int)
    out = zeros.drop(columns=["ml_score"]).merge(
        ml_df[["tmdb_id", "ml_score"]], on="tmdb_id", how="left"
    )
    out["ml_score"] = out["ml_score"].fillna(0.0)
    return out


def hf_channel(content: pd.DataFrame, seed_overviews: list[str]) -> pd.DataFrame:
    """HF plug-in (overview embeddings). Stub = zeros; swap model later."""
    _ = seed_overviews
    return pd.DataFrame({"tmdb_id": content["tmdb_id"], "hf_score": 0.0})


def build_profile_scores(movies: pd.DataFrame | None = None) -> pd.DataFrame:
    movies = load_movies() if movies is None else movies
    links = load_links()
    ratings = load_ratings()
    parts = []

    for profile in DEMO_PROFILES.values():
        content = content_channels(movies, profile.seed_tmdb_ids, profile.mood)
        collab, n_neighbors = collab_channels(movies, profile.seed_tmdb_ids, links, ratings)
        ml = ml_channel(movies, profile.seed_tmdb_ids, links)
        seeds = movies[movies["tmdb_id"].isin(profile.seed_tmdb_ids)]
        seed_overviews = [str(x or "") for x in seeds["overview"].tolist()] if "overview" in seeds else []
        hf = hf_channel(content, seed_overviews)

        merged = (
            content.merge(collab, on="tmdb_id", how="left")
            .merge(ml, on="tmdb_id", how="left")
            .merge(hf, on="tmdb_id", how="left")
        )
        merged["collab_n"] = merged["collab_n"].fillna(0).astype(int)
        merged["collab_avg"] = merged["collab_avg"].fillna(0.0)
        merged["ml_score"] = merged["ml_score"].fillna(0.0)
        merged["hf_score"] = merged["hf_score"].fillna(0.0)
        merged["profile_id"] = profile.profile_id
        merged["neighbor_pool"] = n_neighbors
        parts.append(merged)

    gold = pd.concat(parts, ignore_index=True)
    cols = [
        "profile_id",
        "tmdb_id",
        "title",
        "genres",
        "poster_path",
        "content_score",
        "mood_score",
        "collab_n",
        "collab_avg",
        "ml_score",
        "hf_score",
        "neighbor_pool",
        "content_reason",
    ]
    return gold[cols]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold = build_profile_scores()
    gold.to_parquet(OUT_PARQUET, index=False)
    gold.to_csv(OUT_CSV, index=False)
    print(f"rows={len(gold)} -> {OUT_PARQUET}")


if __name__ == "__main__":
    main()
