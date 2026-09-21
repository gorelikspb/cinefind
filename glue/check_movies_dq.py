"""AWS Glue Python Shell: DQ on S3 silver movies_clean. Job FAILS if a check fails.

  Deploy/run:
    python scripts/deploy_glue_check_movies_dq.py
    python scripts/run_glue_check_movies_dq.py
"""

from __future__ import annotations

import io
import sys

import boto3
import pandas as pd
from awsglue.utils import getResolvedOptions

MIN_ROWS = 1
MIN_JOIN_RATIO = 0.9
MAX_EMPTY_OVERVIEW_RATIO = 0.2
MAX_EMPTY_GENRES_RATIO = 0.05
REQUIRED = ["tmdb_id", "title", "genres", "overview", "movielens_id"]


def main() -> None:
    args = getResolvedOptions(sys.argv, ["BUCKET", "PREFIX"])
    bucket = args["BUCKET"]
    prefix = args["PREFIX"].strip("/")
    s3 = boto3.client("s3")
    errors: list[str] = []

    bronze_prefix = f"{prefix}/bronze/tmdb/movies/"
    n_json = 0
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": bronze_prefix}
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
        errors.append(f"no JSON under s3://{bucket}/{bronze_prefix}")
    else:
        print(f"OK bronze json={n_json}")

    silver_key = f"{prefix}/silver/movies_clean.parquet"
    try:
        body = s3.get_object(Bucket=bucket, Key=silver_key)["Body"].read()
    except Exception as e:
        raise RuntimeError(f"missing s3://{bucket}/{silver_key}: {e}") from e

    df = pd.read_parquet(io.BytesIO(body))
    n = len(df)
    if n < MIN_ROWS:
        errors.append(f"row count {n} < {MIN_ROWS}")
    else:
        print(f"OK rows={n}")

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        errors.append(f"missing columns: {missing}")
    else:
        print(f"OK columns={REQUIRED}")

    dup = int(df["tmdb_id"].duplicated().sum())
    if dup:
        errors.append(f"duplicate tmdb_id={dup}")
    else:
        print("OK no duplicate tmdb_id")

    joined = int(df["movielens_id"].notna().sum())
    join_ratio = joined / n if n else 0.0
    if join_ratio < MIN_JOIN_RATIO:
        errors.append(f"join coverage {join_ratio:.2%} < {MIN_JOIN_RATIO:.0%}")
    else:
        print(f"OK join={join_ratio:.2%} ({joined}/{n})")

    empty_overview = int((df["overview"].fillna("").astype(str).str.strip() == "").sum())
    empty_genres = int((df["genres"].fillna("").astype(str).str.strip() == "").sum())
    if (empty_overview / n if n else 0) > MAX_EMPTY_OVERVIEW_RATIO:
        errors.append("too many empty overview")
    else:
        print(f"OK empty overview={empty_overview}/{n}")
    if (empty_genres / n if n else 0) > MAX_EMPTY_GENRES_RATIO:
        errors.append("too many empty genres")
    else:
        print(f"OK empty genres={empty_genres}/{n}")

    if errors:
        raise RuntimeError("DQ failed: " + "; ".join(errors))
    print(f"all checks passed s3://{bucket}/{silver_key}")


if __name__ == "__main__":
    main()
