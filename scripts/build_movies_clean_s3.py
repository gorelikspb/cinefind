"""Rebuild silver movies_clean from bronze on S3 (runs on your laptop).

Same transform as local / Glue — only I/O differs.
Needs MovieLens CSVs on S3 (`upload_s3_sample.py`).

  python scripts/build_movies_clean_s3.py
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from movies_clean_lib import build_movies_clean  # noqa: E402

BUCKET = os.environ.get("CINEFIND_S3_BUCKET", "cinefind-gorelik-us-east-1")
PREFIX = os.environ.get("CINEFIND_S3_PREFIX", "cinefind").strip("/")


def _read_csv_s3(s3, key: str) -> pd.DataFrame:
    body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(body))


def main() -> None:
    s3 = boto3.client("s3")
    bronze_prefix = f"{PREFIX}/bronze/tmdb/movies/"
    keys = []
    token = None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": bronze_prefix}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for obj in resp.get("Contents") or []:
            if obj["Key"].endswith(".json"):
                keys.append(obj["Key"])
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")

    if not keys:
        raise SystemExit(f"no json under s3://{BUCKET}/{bronze_prefix}")

    rows = []
    for key in sorted(keys):
        body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        rows.append(json.loads(body.decode("utf-8")))

    links = _read_csv_s3(s3, f"{PREFIX}/bronze/movielens/links.csv")
    ml_movies = _read_csv_s3(s3, f"{PREFIX}/bronze/movielens/movies.csv")
    out = build_movies_clean(rows, links, ml_movies)

    buf = io.BytesIO()
    out.to_parquet(buf, index=False)
    silver_key = f"{PREFIX}/silver/movies_clean.parquet"
    s3.put_object(Bucket=BUCKET, Key=silver_key, Body=buf.getvalue())

    matched = int(out["movielens_id"].notna().sum())
    print(f"movies: {len(out)}  joined: {matched}/{len(out)}")
    print(f"wrote s3://{BUCKET}/{silver_key}  (compute=local, data=S3)")


if __name__ == "__main__":
    main()
