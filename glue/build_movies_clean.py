"""AWS Glue Python Shell: bronze JSON on S3 → silver movies_clean.parquet on S3.

Same join logic as scripts/movies_clean_lib.py (kept inline — Glue has one script file).

Job args (defaults match laptop upload layout):
  --BUCKET cinefind-gorelik-us-east-1
  --PREFIX cinefind

Deploy / run from laptop:
  python scripts/deploy_glue_movies_clean.py
  python scripts/run_glue_movies_clean.py
"""

from __future__ import annotations

import io
import json
import sys

import boto3
import pandas as pd
from awsglue.utils import getResolvedOptions


def genres_str(data: dict) -> str:
    names = [g["name"] for g in data.get("genres") or [] if g.get("name")]
    return "|".join(names)


def keywords_str(data: dict) -> str:
    kws = (data.get("keywords") or {}).get("keywords") or []
    names = [k["name"] for k in kws if k.get("name")]
    return "|".join(names)


def row_from_tmdb(data: dict) -> dict:
    return {
        "tmdb_id": data.get("id"),
        "imdb_id": data.get("imdb_id"),
        "title": data.get("title") or data.get("original_title"),
        "original_title": data.get("original_title"),
        "overview": data.get("overview") or "",
        "genres": genres_str(data),
        "keywords": keywords_str(data),
        "release_date": data.get("release_date") or "",
        "runtime": data.get("runtime"),
        "original_language": data.get("original_language"),
        "popularity": data.get("popularity"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "poster_path": data.get("poster_path") or "",
    }


def build_movies_clean(tmdb_rows, links: pd.DataFrame, ml_movies: pd.DataFrame) -> pd.DataFrame:
    tmdb = pd.DataFrame(row_from_tmdb(r) for r in tmdb_rows)
    links = links.dropna(subset=["tmdbId"]).copy()
    links["tmdbId"] = links["tmdbId"].astype(int)
    links = links.rename(
        columns={"movieId": "movielens_id", "tmdbId": "tmdb_id", "imdbId": "imdb_id_ml"}
    )
    ml_movies = ml_movies.rename(
        columns={"movieId": "movielens_id", "title": "title_ml", "genres": "genres_ml"}
    )
    out = tmdb.merge(links[["movielens_id", "tmdb_id"]], on="tmdb_id", how="left")
    return out.merge(ml_movies, on="movielens_id", how="left")


def main() -> None:
    args = getResolvedOptions(sys.argv, ["BUCKET", "PREFIX"])
    bucket = args["BUCKET"]
    prefix = args["PREFIX"].strip("/")
    s3 = boto3.client("s3")

    bronze_prefix = f"{prefix}/bronze/tmdb/movies/"
    keys = []
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": bronze_prefix}
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
        raise RuntimeError(f"no json under s3://{bucket}/{bronze_prefix}")

    rows = []
    for key in sorted(keys):
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        rows.append(json.loads(body.decode("utf-8")))

    links_obj = s3.get_object(Bucket=bucket, Key=f"{prefix}/bronze/movielens/links.csv")
    movies_obj = s3.get_object(Bucket=bucket, Key=f"{prefix}/bronze/movielens/movies.csv")
    links = pd.read_csv(io.BytesIO(links_obj["Body"].read()))
    ml_movies = pd.read_csv(io.BytesIO(movies_obj["Body"].read()))

    out = build_movies_clean(rows, links, ml_movies)
    buf = io.BytesIO()
    out.to_parquet(buf, index=False)
    silver_key = f"{prefix}/silver/movies_clean.parquet"
    s3.put_object(Bucket=bucket, Key=silver_key, Body=buf.getvalue())
    print(f"movies={len(out)} wrote s3://{bucket}/{silver_key}")


if __name__ == "__main__":
    main()
