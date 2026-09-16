"""Pull a few TMDb movies and save JSON. Default: 3 requests (local test)."""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "links.csv"
OUT = ROOT / "data" / "raw_private" / "tmdb" / "movies"

N = 50  # how many movies to fetch
SLEEP = 1.0  # pause between movies
RETRIES = 8  # network to TMDb is flaky here

# load .env into process env
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "cinefind-local",
            "Connection": "close",  # avoid broken keep-alive
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_movie(tmdb_id: int, key: str) -> dict:
    q = urllib.parse.urlencode({"api_key": key, "append_to_response": "keywords"})
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?{q}"
    last: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            return get_json(url)
        except urllib.error.URLError as e:
            last = e
            wait = attempt  # 1s, 2s, 3s...
            print(f"  retry {attempt}/{RETRIES} after error, wait {wait}s")
            time.sleep(wait)
    raise last  # type: ignore[misc]


def main() -> None:
    key = os.environ["TMDB_API_KEY"]
    OUT.mkdir(parents=True, exist_ok=True)

    ids: list[int] = []
    with LINKS.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("tmdbId"):
                ids.append(int(float(row["tmdbId"])))
            if len(ids) >= N:
                break

    ok = 0
    for i, tmdb_id in enumerate(ids, start=1):
        path = OUT / f"{tmdb_id}.json"
        if path.exists():
            print(f"[{i}/{N}] skip {tmdb_id} (exists)")
            ok += 1
            continue
        print(f"[{i}/{N}] fetching {tmdb_id}...")
        try:
            data = fetch_movie(tmdb_id, key)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{i}/{N}] ok — {data.get('title')}")
            ok += 1
        except Exception as e:
            print(f"[{i}/{N}] failed {tmdb_id}: {e}")
        time.sleep(SLEEP)

    print(f"done: {ok}/{N} saved in {OUT}")


if __name__ == "__main__":
    main()
