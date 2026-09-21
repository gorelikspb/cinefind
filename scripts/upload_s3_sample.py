"""Upload local bronze/silver preview to S3 (small-batch cloud land).

Env (optional):
  CINEFIND_S3_BUCKET  default cinefind-gorelik-us-east-1
  CINEFIND_S3_PREFIX  default cinefind

Layout:
  s3://{bucket}/{prefix}/bronze/tmdb/movies/*.json
  s3://{bucket}/{prefix}/silver/movies_clean.parquet

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
LOCAL_CLEAN = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"


def main() -> None:
    s3 = boto3.client("s3")
    n_json = 0
    for path in sorted(LOCAL_TMDB.glob("*.json")):
        key = f"{PREFIX}/bronze/tmdb/movies/{path.name}"
        s3.upload_file(str(path), BUCKET, key)
        n_json += 1
    print(f"uploaded {n_json} json -> s3://{BUCKET}/{PREFIX}/bronze/tmdb/movies/")

    if not LOCAL_CLEAN.exists():
        raise SystemExit(f"missing {LOCAL_CLEAN} — run build_movies_clean.py first")
    clean_key = f"{PREFIX}/silver/movies_clean.parquet"
    s3.upload_file(str(LOCAL_CLEAN), BUCKET, clean_key)
    print(f"uploaded silver -> s3://{BUCKET}/{clean_key}")


if __name__ == "__main__":
    main()
