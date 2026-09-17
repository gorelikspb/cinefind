"""Demo profile → top-10 on movies_clean (rules score + reason). DQ is separate."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MOVIES = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"
OUT_DIR = ROOT / "data" / "raw_private" / "preview"
OUT_CSV = OUT_DIR / "demo_top10.csv"

# demo profile — edit here
PROFILE_ID = "demo_family"
SEED_TMDB_IDS = [862, 8844, 21032]  # Toy Story, Jumanji, Balto
MOOD = "family"  # "" to disable
TOP_N = 10

W_GENRE = 3.0
W_KEYWORD = 2.0
W_MOOD = 2.0
W_VOTE = 1.0  # vote_average 7 → +7


def split_pipe(value: object) -> set[str]:
    """'Family|Comedy' → {'family', 'comedy'} for set intersection."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {p.strip().lower() for p in text.split("|") if p.strip()}


def mood_hit(row: pd.Series, mood: str) -> bool:
    """Mood word found in genres / keywords / overview / title."""
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
    """Overlap with seeds + optional mood + vote_average → (score, reason)."""
    genres = split_pipe(row.get("genres"))
    keywords = split_pipe(row.get("keywords"))
    shared_g = sorted(genres & seed_genres)
    shared_k = sorted(keywords & seed_keywords)

    score = W_GENRE * len(shared_g) + W_KEYWORD * len(shared_k)
    reasons: list[str] = []
    if shared_g:
        reasons.append("genres:" + ",".join(shared_g))
    if shared_k:
        reasons.append("keywords:" + ",".join(shared_k[:8]))
    if mood_hit(row, mood):
        score += W_MOOD
        reasons.append(f"mood:{mood}")

    vote = row.get("vote_average")
    if vote is not None and not pd.isna(vote):
        score += W_VOTE * float(vote)
        reasons.append(f"vote:{float(vote):.1f}")

    return score, ("; ".join(reasons) if reasons else "weak match")


def main() -> None:
    movies = pd.read_parquet(MOVIES)

    seeds = movies[movies["tmdb_id"].isin(SEED_TMDB_IDS)]
    if len(seeds) != len(SEED_TMDB_IDS):
        found = set(seeds["tmdb_id"].tolist())
        missing = [i for i in SEED_TMDB_IDS if i not in found]
        raise SystemExit(f"Seed movies missing from movies_clean: {missing}")

    # taste profile = union of seed genres/keywords
    seed_genres: set[str] = set()
    seed_keywords: set[str] = set()
    for _, row in seeds.iterrows():
        seed_genres |= split_pipe(row.get("genres"))
        seed_keywords |= split_pipe(row.get("keywords"))

    cand = movies[~movies["tmdb_id"].isin(SEED_TMDB_IDS)].copy()

    scored = []
    for _, row in cand.iterrows():
        s, reason = score_row(row, seed_genres, seed_keywords, MOOD)
        scored.append(
            {
                "profile_id": PROFILE_ID,
                "tmdb_id": row["tmdb_id"],
                "title": row["title"],
                "genres": row.get("genres"),
                "score": round(s, 3),
                "reason": reason,
            }
        )

    out = pd.DataFrame(scored).sort_values("score", ascending=False).head(TOP_N)
    out.insert(0, "rank", range(1, len(out) + 1))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    print(f"profile: {PROFILE_ID}")
    print("seeds:", ", ".join(seeds["title"].astype(str)))
    print(f"mood: {MOOD or '(none)'}")
    print(f"seed genres: {sorted(seed_genres)}")
    print()
    print(out[["rank", "title", "score", "reason"]].to_string(index=False))
    print(f"\nwrote {OUT_CSV}")


if __name__ == "__main__":
    main()
