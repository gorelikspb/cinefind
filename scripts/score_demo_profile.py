"""Demo profiles → top-10 CSV files (uses scoring_lib)."""

from __future__ import annotations

import pandas as pd

from scoring_lib import DEMO_PROFILES, OUT_DIR, load_movies, score_profile


def main() -> None:
    movies = load_movies()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for profile in DEMO_PROFILES.values():
        payload = score_profile(movies, profile)
        rows = [
            {
                "rank": r["rank"],
                "profile_id": profile.profile_id,
                "tmdb_id": r["tmdb_id"],
                "title": r["title"],
                "genres": r["genres"],
                "score": r["score"],
                "reason": r["reason"],
            }
            for r in payload["results"]
        ]
        out = pd.DataFrame(rows)
        path = OUT_DIR / f"{profile.profile_id}_top10.csv"
        out.to_csv(path, index=False)

        print(f"profile: {profile.profile_id} ({profile.label})")
        print("seeds:", ", ".join(s["title"] for s in payload["seeds"]))
        print(f"mood: {profile.mood or '(none)'}")
        print(out[["rank", "title", "score"]].to_string(index=False))
        print(f"wrote {path}\n")

    # keep legacy filename for the family profile
    legacy = OUT_DIR / "demo_family_top10.csv"
    demo = OUT_DIR / "demo_top10.csv"
    if legacy.exists():
        demo.write_bytes(legacy.read_bytes())
        print(f"also wrote {demo}")


if __name__ == "__main__":
    main()
