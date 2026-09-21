"""DQ on S3 silver movies_clean (+ bronze JSON count). Exit 1 if a check fails.

Same rules as check_movies_dq.py — data on S3 instead of local disk.

  python scripts/check_movies_dq_s3.py
"""

from __future__ import annotations

import io
import os
import sys

import boto3
import pandas as pd

BUCKET = os.environ.get("CINEFIND_S3_BUCKET", "cinefind-gorelik-us-east-1")
PREFIX = os.environ.get("CINEFIND_S3_PREFIX", "cinefind").strip("/")

MIN_ROWS = 1
MIN_JOIN_RATIO = 0.9
MAX_EMPTY_OVERVIEW_RATIO = 0.2
MAX_EMPTY_GENRES_RATIO = 0.05
REQUIRED = ["tmdb_id", "title", "genres", "overview", "movielens_id"]


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"OK:   {msg}")


def main() -> int:
    s3 = boto3.client("s3")
    errors: list[str] = []

    bronze_prefix = f"{PREFIX}/bronze/tmdb/movies/"
    n_json = 0
    token = None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": bronze_prefix}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for obj in resp.get("Contents") or []:
            if obj["Key"].endswith(".json"):
                n_json += 1
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")

    if n_json < 1:
        fail(f"no TMDb JSON under s3://{BUCKET}/{bronze_prefix}", errors)
    else:
        ok(f"bronze TMDb JSON objects: {n_json}")

    silver_key = f"{PREFIX}/silver/movies_clean.parquet"
    try:
        body = s3.get_object(Bucket=BUCKET, Key=silver_key)["Body"].read()
    except s3.exceptions.NoSuchKey:
        fail(f"missing s3://{BUCKET}/{silver_key} — run Glue / build_movies_clean_s3 first", errors)
        print(f"\n{len(errors)} check(s) failed")
        return 1
    except Exception as e:
        # ClientError NoSuchKey varies by botocore version
        if "NoSuchKey" in type(e).__name__ or "404" in str(e) or "Not Found" in str(e):
            fail(f"missing s3://{BUCKET}/{silver_key}", errors)
            print(f"\n{len(errors)} check(s) failed")
            return 1
        raise

    df = pd.read_parquet(io.BytesIO(body))
    n = len(df)
    if n < MIN_ROWS:
        fail(f"row count {n} < MIN_ROWS {MIN_ROWS}", errors)
    else:
        ok(f"row count: {n}")

    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        fail(f"missing columns: {missing_cols}", errors)
        print(f"\n{len(errors)} check(s) failed")
        return 1
    ok(f"required columns present: {REQUIRED}")

    dup = int(df["tmdb_id"].duplicated().sum())
    if dup > 0:
        fail(f"duplicate tmdb_id rows: {dup}", errors)
    else:
        ok("no duplicate tmdb_id")

    joined = int(df["movielens_id"].notna().sum())
    join_ratio = joined / n if n else 0.0
    if join_ratio < MIN_JOIN_RATIO:
        fail(f"join coverage {join_ratio:.2%} ({joined}/{n}) < {MIN_JOIN_RATIO:.0%}", errors)
    else:
        ok(f"join coverage: {join_ratio:.2%} ({joined}/{n})")

    empty_overview = int((df["overview"].fillna("").astype(str).str.strip() == "").sum())
    empty_genres = int((df["genres"].fillna("").astype(str).str.strip() == "").sum())
    ov_ratio = empty_overview / n if n else 0.0
    ge_ratio = empty_genres / n if n else 0.0

    if ov_ratio > MAX_EMPTY_OVERVIEW_RATIO:
        fail(f"empty overview {ov_ratio:.2%} > {MAX_EMPTY_OVERVIEW_RATIO:.0%}", errors)
    else:
        ok(f"empty overview: {empty_overview}/{n}")

    if ge_ratio > MAX_EMPTY_GENRES_RATIO:
        fail(f"empty genres {ge_ratio:.2%} > {MAX_EMPTY_GENRES_RATIO:.0%}", errors)
    else:
        ok(f"empty genres: {empty_genres}/{n}")

    if errors:
        print(f"\n{len(errors)} check(s) failed")
        return 1
    print(f"\nall checks passed  (s3://{BUCKET}/{silver_key})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
