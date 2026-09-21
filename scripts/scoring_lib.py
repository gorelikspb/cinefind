"""Demo profiles, content rules, and rank-from-gold (weighted channels)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MOVIES_PATH = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"
PROFILE_SCORES_PATH = ROOT / "data" / "raw_private" / "preview" / "profile_scores.parquet"
OUT_DIR = ROOT / "data" / "raw_private" / "preview"

W_GENRE = 3.0
W_KEYWORD = 2.0
W_VOTE = 1.0
TOP_N = 10
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w342"
TMDB_MOVIE_BASE = "https://www.themoviedb.org/movie"

@dataclass(frozen=True)
class DemoProfile:
    profile_id: str
    label: str
    seed_tmdb_ids: tuple[int, ...]
    mood: str


DEMO_PROFILES: dict[str, DemoProfile] = {
    "demo_family": DemoProfile("demo_family", "Family / kids adventure", (862, 8844, 21032), "family"),
    "demo_crime": DemoProfile("demo_crime", "Crime / thriller", (949, 524, 807), "crime"),
    "demo_romance": DemoProfile("demo_romance", "Romance / drama", (11860, 4584, 9603), "romance"),
}


def split_pipe(value: object) -> set[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {p.strip().lower() for p in text.split("|") if p.strip()}


def mood_hit(row: pd.Series, mood: str) -> bool:
    if not mood:
        return False
    m = mood.lower()
    blob = " ".join(
        str(row.get(c) or "") for c in ("genres", "keywords", "overview", "title")
    ).lower()
    return m in blob


def score_row(row, seed_genres, seed_keywords) -> tuple[float, str]:
    """Genre/keyword/vote only. Mood is a separate gold column."""
    genres = split_pipe(row.get("genres"))
    keywords = split_pipe(row.get("keywords"))
    shared_g = sorted(genres & seed_genres)
    shared_k = sorted(keywords & seed_keywords)
    score = W_GENRE * len(shared_g) + W_KEYWORD * len(shared_k)
    reasons = []
    if shared_g:
        reasons.append("genres:" + ",".join(shared_g))
    if shared_k:
        reasons.append("keywords:" + ",".join(shared_k[:8]))
    vote = row.get("vote_average")
    if vote is not None and not pd.isna(vote):
        score += W_VOTE * float(vote)
        reasons.append(f"vote:{float(vote):.1f}")
    return score, ("; ".join(reasons) if reasons else "weak match")


def mood_score(row, mood: str) -> float:
    return 1.0 if mood_hit(row, mood) else 0.0


def load_movies(path: Path = MOVIES_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_profile_scores(path: Path = PROFILE_SCORES_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def poster_url(poster_path: object) -> str | None:
    if poster_path is None or (isinstance(poster_path, float) and pd.isna(poster_path)):
        return None
    path = str(poster_path).strip()
    if not path:
        return None
    return path if path.startswith("http") else f"{TMDB_POSTER_BASE}{path}"


def tmdb_url(tmdb_id: object) -> str | None:
    if tmdb_id is None or (isinstance(tmdb_id, float) and pd.isna(tmdb_id)):
        return None
    return f"{TMDB_MOVIE_BASE}/{int(tmdb_id)}"


def _minmax(series: pd.Series) -> pd.Series:
    lo, hi = float(series.min()), float(series.max())
    if hi <= lo:
        return pd.Series(0.0, index=series.index)
    return (series.astype(float) - lo) / (hi - lo)


def rank_from_gold(
    gold: pd.DataFrame,
    profile: DemoProfile,
    movies: pd.DataFrame,
    *,
    w_content: float = 1.0,
    w_mood: float = 1.0,
    w_collab_n: float = 1.0,
    w_collab_avg: float = 1.0,
    w_ml: float = 0.0,
    w_hf: float = 0.0,
    top_n: int = TOP_N,
) -> dict:
    seeds = movies[movies["tmdb_id"].isin(profile.seed_tmdb_ids)]
    g = gold[gold["profile_id"] == profile.profile_id].copy()
    if g.empty:
        raise ValueError(f"no gold rows for {profile.profile_id}")

    for col, default in (("ml_score", 0.0), ("hf_score", 0.0), ("mood_score", 0.0)):
        if col not in g.columns:
            g[col] = default

    g["c_n"] = _minmax(g["content_score"])
    g["mood_n"] = _minmax(g["mood_score"])
    g["n_n"] = _minmax(g["collab_n"])
    g["a_n"] = _minmax(g["collab_avg"])
    g["m_n"] = _minmax(g["ml_score"])
    g["h_n"] = _minmax(g["hf_score"])
    g["final"] = (
        w_content * g["c_n"]
        + w_mood * g["mood_n"]
        + w_collab_n * g["n_n"]
        + w_collab_avg * g["a_n"]
        + w_ml * g["m_n"]
        + w_hf * g["h_n"]
    )
    g = g.sort_values(["final", "content_score"], ascending=False).head(top_n)

    results = []
    for i, row in enumerate(g.itertuples(), start=1):
        tid = int(row.tmdb_id)
        results.append(
            {
                "rank": i,
                "tmdb_id": tid,
                "title": row.title,
                "genres": row.genres,
                "score": round(float(row.final), 3),
                "content_score": round(float(row.content_score), 3),
                "mood_score": round(float(row.mood_score), 3),
                "collab_n": int(row.collab_n),
                "collab_avg": round(float(row.collab_avg), 3),
                "ml_score": round(float(row.ml_score), 3),
                "hf_score": round(float(row.hf_score), 3),
                "reason": (
                    f"final={row.final:.3f} "
                    f"raw c={row.content_score:.1f} mood={row.mood_score:.0f} "
                    f"n={int(row.collab_n)} avg={row.collab_avg:.2f} "
                    f"ml={row.ml_score:.3f} hf={row.hf_score:.3f}"
                ),
                "poster_url": poster_url(getattr(row, "poster_path", None)),
                "tmdb_url": tmdb_url(tid),
            }
        )

    return {
        "profile_id": profile.profile_id,
        "label": profile.label,
        "mood": profile.mood,
        "weights": {
            "content": float(w_content),
            "mood": float(w_mood),
            "collab_n": float(w_collab_n),
            "collab_avg": float(w_collab_avg),
            "ml": float(w_ml),
            "hf": float(w_hf),
        },
        "neighbor_pool": int(g["neighbor_pool"].iloc[0]) if len(g) else 0,
        "seeds": [
            {
                "tmdb_id": int(r.tmdb_id),
                "title": r.title,
                "poster_url": poster_url(getattr(r, "poster_path", None)),
                "tmdb_url": tmdb_url(r.tmdb_id),
            }
            for r in seeds.itertuples()
        ],
        "results": results,
    }


def score_profile(
    movies: pd.DataFrame,
    profile: DemoProfile,
    top_n: int = TOP_N,
    *,
    gold: pd.DataFrame | None = None,
    w_content: float = 1.0,
    w_mood: float = 1.0,
    w_collab_n: float = 1.0,
    w_collab_avg: float = 1.0,
    w_ml: float = 0.0,
    w_hf: float = 0.0,
) -> dict:
    if gold is None:
        gold = load_profile_scores()
    return rank_from_gold(
        gold,
        profile,
        movies,
        w_content=w_content,
        w_mood=w_mood,
        w_collab_n=w_collab_n,
        w_collab_avg=w_collab_avg,
        w_ml=w_ml,
        w_hf=w_hf,
        top_n=top_n,
    )
