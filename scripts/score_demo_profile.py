"""Build gold profile_scores + write demo top10 CSVs."""

from __future__ import annotations

import pandas as pd

from build_profile_scores import OUT_CSV, OUT_PARQUET, build_profile_scores
from scoring_lib import DEMO_PROFILES, OUT_DIR, load_movies, score_profile


def main() -> None:
    movies = load_movies()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold = build_profile_scores(movies)
    gold.to_parquet(OUT_PARQUET, index=False)
    gold.to_csv(OUT_CSV, index=False)
    print(f"gold rows={len(gold)} -> {OUT_PARQUET}")

    for profile in DEMO_PROFILES.values():
        payload = score_profile(movies, profile, gold=gold)
        rows = [
            {
                "rank": r["rank"],
                "profile_id": profile.profile_id,
                "tmdb_id": r["tmdb_id"],
                "title": r["title"],
                "score": r["score"],
                "content_score": r["content_score"],
                "mood_score": r["mood_score"],
                "collab_n": r["collab_n"],
                "ml_score": r["ml_score"],
                "hf_score": r["hf_score"],
            }
            for r in payload["results"]
        ]
        path = OUT_DIR / f"{profile.profile_id}_top10.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        print(profile.profile_id, [r["title"] for r in payload["results"][:3]])


if __name__ == "__main__":
    main()
