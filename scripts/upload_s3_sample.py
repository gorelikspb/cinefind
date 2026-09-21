"""Upload local bronze (+ MovieLens CSVs) to S3. Optional: also copy local silver.

  python scripts/upload_s3_sample.py
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
BUCKET = os.environ.get("CINEFIND_S3_BUCKET", "cinefind-gorelik-us-east-1")
PREFIX = os.environ.get("CINEFIND_S3_PREFIX", "cinefind").strip("/")

LOCAL_TMDB = ROOT / "data" / "raw_private" / "tmdb" / "movies"
LOCAL_LINKS = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "links.csv"
LOCAL_MOVIES = ROOT / "data" / "raw_private" / "movielens" / "ml-latest-small" / "movies.csv"
LOCAL_CLEAN = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"


def main() -> None:
    s3 = boto3.client("s3")
    n_json = 0
    for path in sorted(LOCAL_TMDB.glob("*.json")):
        key = f"{PREFIX}/bronze/tmdb/movies/{path.name}"
        s3.upload_file(str(path), BUCKET, key)
        n_json += 1
    print(f"uploaded {n_json} json -> s3://{BUCKET}/{PREFIX}/bronze/tmdb/movies/")

    for local, name in ((LOCAL_LINKS, "links.csv"), (LOCAL_MOVIES, "movies.csv")):
        key = f"{PREFIX}/bronze/movielens/{name}"
        s3.upload_file(str(local), BUCKET, key)
        print(f"uploaded {name} -> s3://{BUCKET}/{key}")

    # Optional snapshot of local silver (cloud rebuild should overwrite this).
    if LOCAL_CLEAN.exists():
        clean_key = f"{PREFIX}/silver/movies_clean.parquet"
        s3.upload_file(str(LOCAL_CLEAN), BUCKET, clean_key)
        print(f"uploaded local silver snapshot -> s3://{BUCKET}/{clean_key}")


if __name__ == "__main__":
    main()
