# Architecture (draft sketch)

Status: **rough draft** — will change after local clean table + coach feedback.  
Pipeline story lives **here**. Day-to-day notes stay in `docs/progress.md`.

## Goal

CineFind: recommend movies from a few seed titles (+ optional mood). Capstone focus = data pipeline + a demo.

## Sources

- **TMDb** — movie info (title, genres, overview, keywords, …)
- **MovieLens** — ratings / tags / `links` (bridge to `tmdbId`)
- Later maybe Trakt for trending (optional)

## Layers (medallion-style)

```text
Sources (TMDb API, MovieLens files)
    → Bronze / raw     check raw data
    → Silver           processed tables (Parquet; later maybe Delta)
    → Gold             feature tables / feature store / scored outputs
    → Serve            table / Metabase / small API
```

### Bronze (raw)

- Land data as ingested: TMDb JSON, MovieLens CSVs.
- **Check raw data** before promoting: files exist, readable, expected columns/ids, row counts sensible, basic null spikes.
- Storage later: **S3, ADLS Gen2**. Local folder works for debug.

### Silver (processed)

- Clean / join / type / dedupe.
- Output as **Parquet** (columnar, easy to scale). **Delta Lake** (Parquet files + a transaction log: updates, time travel, ACID on the lake) is an option if we run Databricks-style jobs.
- Example tables: `movies_clean`, maybe `ratings_clean`, `links`.
- Transform engine when we leave pure local: **Glue, Databricks / PySpark, Pandas / Polars**.

### Gold (calculated / trained / ready to serve)

Silver holds cleaned facts. Gold holds **derived** tables built from silver:

- **Feature tables** — calculated columns per movie (or profile): genre flags, keyword bags, popularity bins; embeddings later if we train them
- **Feature store** — reusable, versioned feature tables (e.g. `movie_features` in **Parquet, Delta**) that scoring and future models read
- **Scored / trained outputs** — rules or model results, e.g. `rec_movies_scored` (profile, movie, score, reason) plus an optional model version

MVP path: build features → rules-based score → top-N (explainable).  
Optional later: train embeddings or a small model and write predictions into the same gold layer.

Compute: **Glue, Spark / Databricks, local Python**. Serving reads gold.

### Serve

- **Metabase, Athena / Spark SQL, FastAPI** — enough to show top-10.
  Local demo: `serve/app.py` exposes three fixed profiles as JSON (`/v1/recommendations/{profile_id}`).

## Data quality (in the pipeline)

Quality runs as a **pipeline step**. Failed checks fail the run.

Ideas (draft):

| Stage | Checks (examples) |
|-------|-------------------|
| After bronze | file present, row count > 0, required fields exist, `tmdbId` parseable |
| After silver | no dup primary keys, join coverage, genres/overview present, schema stable |
| After gold | top-N size, scores finite, seed movies excluded from results |

Tools: **Great Expectations, Deequ, assert/SQL checks**. Orchestrator: **Airflow, Databricks Jobs**.

“Glue script checking” means validation inside the transform job (same pattern on Databricks / PySpark).

## Scale story

Official [MovieLens](https://grouplens.org/datasets/movielens/) sizes (ratings, approx.):

| Dataset | Ratings (order of) |
|---------|-------------------|
| `ml-latest-small` | ~100k |
| ML 100K / 1M / 10M / 20M / 25M | 100k → 25M |
| ML 32M (stable, 2024) | ~32M |
| `ml-latest` (full, changes over time) | ~33M |
| ML 1B synthetic (MLPerf expansion of 20M) | ~1B |

We debug on **`ml-latest-small`**. The pipeline should still make sense if we later load **25M / 32M** (or the 1B synthetic set) with the same layers and more Spark workers.

## Orchestration & ops

- Local proof: **Airflow** under `airflow/` (Docker Compose, LocalExecutor). DAG `cinefind_local`: `build_movies_clean` → `check_movies_dq` → `score_demo_profile`. UI `http://localhost:8080` (user/pass `airflow` / `airflow`).
- Cloud later: same task order on **Airflow** (AWS path) or **Databricks Jobs** (Azure path).
- Secrets: env / secret store (never in git)
- Metrics / alerts later: job duration, rows in/out, fail rate (**CloudWatch, Databricks metrics**)

## Cloud choice (parked)

Bootcamp path: **S3 + Glue + Athena + Airflow**.  
Alternative path: **ADLS + Azure Databricks / PySpark / Delta Lake**.  
Layers stay the same; the cloud product names change. Decide after local clean table + demo top-10.

## Out of scope for this sketch

Full consumer UI and heavy ML on day one.
