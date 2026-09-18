"""Shared rules scoring + demo profiles for CLI and API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MOVIES_PATH = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"
OUT_DIR = ROOT / "data" / "raw_private" / "preview"

# Score weights (demo rules engine — not ML).
W_GENRE = 3.0  # per shared genre with the seed taste set
W_KEYWORD = 2.0  # per shared keyword
W_MOOD = 2.0  # flat bonus if mood word appears on the candidate
W_VOTE = 1.0  # times TMDb vote_average (e.g. 7.0 → +7)
TOP_N = 10
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w342"
TMDB_MOVIE_BASE = "https://www.themoviedb.org/movie"


@dataclass(frozen=True)
class DemoProfile:
    profile_id: str
    label: str
    seed_tmdb_ids: tuple[int, ...]
    mood: str


# Seeds must exist in the local movies_clean sample.
DEMO_PROFILES: dict[str, DemoProfile] = {
    "demo_family": DemoProfile(
        profile_id="demo_family",
        label="Family / kids adventure",
        seed_tmdb_ids=(862, 8844, 21032),  # Toy Story, Jumanji, Balto
        mood="family",
    ),
    "demo_crime": DemoProfile(
        profile_id="demo_crime",
        label="Crime / thriller",
        seed_tmdb_ids=(949, 524, 807),  # Heat, Casino, Se7en
        mood="crime",
    ),
    "demo_romance": DemoProfile(
        profile_id="demo_romance",
        label="Romance / drama",
        seed_tmdb_ids=(11860, 4584, 9603),  # Sabrina, Sense and Sensibility, Clueless
        mood="romance",
    ),
}


def split_pipe(value: object) -> set[str]:
    """'Family|Comedy' → {'family', 'comedy'} for set intersection in scoring."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {p.strip().lower() for p in text.split("|") if p.strip()}


def mood_hit(row: pd.Series, mood: str) -> bool:
    """True if mood substring appears in genres / keywords / overview / title."""
    if not mood:
        return False
    m = mood.lower()
    blob = " ".join(
        [
            str(row.get("genres") or ""),
            str(row.get("keywords") or ""),
            str(row.get("overview") or ""),
            str(row.get("title") or ""),
        ]
    ).lower()
    return m in blob


def score_row(
    row: pd.Series,
    seed_genres: set[str],
    seed_keywords: set[str],
    mood: str,
) -> tuple[float, str]:
    """Score one candidate vs seed taste: overlap + mood + vote → (score, reason)."""
    genres = split_pipe(row.get("genres"))
    keywords = split_pipe(row.get("keywords"))
    # Shared tags with the seed union (order only for stable reason text).
    shared_g = sorted(genres & seed_genres)
    shared_k = sorted(keywords & seed_keywords)

    # Main signal: how many seed genres/keywords this movie also has.
    score = W_GENRE * len(shared_g) + W_KEYWORD * len(shared_k)
    reasons: list[str] = []
    if shared_g:
        reasons.append("genres:" + ",".join(shared_g))
    if shared_k:
        reasons.append("keywords:" + ",".join(shared_k[:8]))
    # Optional mood word from the demo profile.
    if mood_hit(row, mood):
        score += W_MOOD
        reasons.append(f"mood:{mood}")

    # Light quality nudge from TMDb; same scale for every candidate.
    vote = row.get("vote_average")
    if vote is not None and not pd.isna(vote):
        score += W_VOTE * float(vote)
        reasons.append(f"vote:{float(vote):.1f}")

    return score, ("; ".join(reasons) if reasons else "weak match")


def load_movies(path: Path = MOVIES_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing {path} — run build_movies_clean.py first")
    return pd.read_parquet(path)


def poster_url(poster_path: object) -> str | None:
    if poster_path is None or (isinstance(poster_path, float) and pd.isna(poster_path)):
        return None
    path = str(poster_path).strip()
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{TMDB_POSTER_BASE}{path}"


def tmdb_url(tmdb_id: object) -> str | None:
    if tmdb_id is None or (isinstance(tmdb_id, float) and pd.isna(tmdb_id)):
        return None
    return f"{TMDB_MOVIE_BASE}/{int(tmdb_id)}"


def score_profile(
    movies: pd.DataFrame,
    profile: DemoProfile,
    top_n: int = TOP_N,
) -> dict:
    """Build taste from seeds, score every other movie, return top_n."""
    seeds = movies[movies["tmdb_id"].isin(profile.seed_tmdb_ids)]
    found = set(seeds["tmdb_id"].tolist())
    missing = [i for i in profile.seed_tmdb_ids if i not in found]
    if missing:
        raise ValueError(f"{profile.profile_id}: seed movies missing from movies_clean: {missing}")

    # Taste profile = union of seed genres/keywords (set: 1 or 2 seeds with
    # Action still counts as one Action in the profile).
    seed_genres: set[str] = set()
    seed_keywords: set[str] = set()
    for _, row in seeds.iterrows():
        seed_genres |= split_pipe(row.get("genres"))
        seed_keywords |= split_pipe(row.get("keywords"))

    # Do not recommend the seeds themselves.
    cand = movies[~movies["tmdb_id"].isin(profile.seed_tmdb_ids)]
    scored = []
    for _, row in cand.iterrows():
        s, reason = score_row(row, seed_genres, seed_keywords, profile.mood)
        tid = int(row["tmdb_id"])
        scored.append(
            {
                "rank": 0,
                "tmdb_id": tid,
                "title": row["title"],
                "genres": row.get("genres"),
                "score": round(s, 3),
                "reason": reason,
                "poster_url": poster_url(row.get("poster_path")),
                "tmdb_url": tmdb_url(tid),
            }
        )

    # Highest score first; assign 1..top_n ranks.
    out = sorted(scored, key=lambda r: r["score"], reverse=True)[:top_n]
    for i, row in enumerate(out, start=1):
        row["rank"] = i

    return {
        "profile_id": profile.profile_id,
        "label": profile.label,
        "mood": profile.mood,
        "seeds": [
            {
                "tmdb_id": int(r.tmdb_id),
                "title": r.title,
                "poster_url": poster_url(getattr(r, "poster_path", None)),
                "tmdb_url": tmdb_url(r.tmdb_id),
            }
            for r in seeds.itertuples()
        ],
        "results": out,
    }
