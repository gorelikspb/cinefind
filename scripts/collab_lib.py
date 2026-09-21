"""MovieLens collaborative neighbors → collab_n / collab_avg for gold."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LINKS_PATH = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "links.csv"
RATINGS_PATH = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "ratings.csv"

LIKE_MIN = 4.0
MIN_SEED_HITS = 2


def load_links(path: Path = LINKS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path).dropna(subset=["tmdbId"]).copy()
    df["tmdb_id"] = df["tmdbId"].astype(int)
    df["movieId"] = df["movieId"].astype(int)
    return df[["movieId", "tmdb_id"]]


def load_ratings(path: Path = RATINGS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df[["userId", "movieId", "rating"]].astype({"userId": int, "movieId": int, "rating": float})


def tmdb_ids_to_movie_ids(tmdb_ids, links: pd.DataFrame) -> list[int]:
    by_tmdb = dict(zip(links["tmdb_id"], links["movieId"]))
    return [int(by_tmdb[int(t)]) for t in tmdb_ids if int(t) in by_tmdb]


def find_neighbor_user_ids(
    ratings: pd.DataFrame,
    seed_movie_ids: list[int],
    *,
    like_min: float = LIKE_MIN,
    min_seed_hits: int = MIN_SEED_HITS,
) -> list[int]:
    if not seed_movie_ids:
        return []
    likes = ratings[
        (ratings["movieId"].isin(seed_movie_ids)) & (ratings["rating"] >= like_min)
    ]
    hits = likes.groupby("userId")["movieId"].nunique()
    return hits[hits >= min_seed_hits].index.astype(int).tolist()


def collab_candidate_scores(
    ratings: pd.DataFrame,
    neighbor_ids: list[int],
    seed_movie_ids: list[int],
    allowed_movie_ids: set[int],
    *,
    like_min: float = LIKE_MIN,
) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["movieId", "n_likers", "avg_rating", "score"])
    if not neighbor_ids:
        return empty
    liked = ratings[
        (ratings["userId"].isin(neighbor_ids))
        & (ratings["rating"] >= like_min)
        & (~ratings["movieId"].isin(seed_movie_ids))
        & (ratings["movieId"].isin(allowed_movie_ids))
    ]
    if liked.empty:
        return empty
    agg = (
        liked.groupby("movieId")
        .agg(n_likers=("userId", "nunique"), avg_rating=("rating", "mean"))
        .reset_index()
    )
    agg["score"] = agg["n_likers"] + agg["avg_rating"]
    return agg.sort_values(["score", "n_likers"], ascending=False)
