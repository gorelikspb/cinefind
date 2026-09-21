# Runbook (local)

Repo root `cinefind/`. `.env` with `TMDB_API_KEY`, venv + `requirements.txt`, MovieLens under `data/raw_private/movielens/`.

## Pipeline

```powershell
python scripts/fetch_tmdb_movies.py
python scripts/build_movies_clean.py
python scripts/check_movies_dq.py
python scripts/train_cf_svd.py          # optional; ml_score=0 without it
python scripts/score_demo_profile.py    # gold + top10 csv
```

Airflow (`airflow/`): choose silver local|glue → DQ → gold.  
Fetch and train are optional / separate.

```powershell
cd airflow
docker compose up -d --pull never
```

UI: http://localhost:8080 — `airflow` / `airflow`  
DAG `cinefind_local`: unpause → Trigger.

```powershell
docker compose down
```

## Serve

From repo root `cinefind/`:

```powershell
python -m uvicorn serve.app:app --reload --port 8001
```

http://localhost:8001 — sliders on gold channels (`docs/scoring.md`).

If the port is already taken by **this same** app — don't kill the process; just open the URL.  
With `--reload`, code edits are picked up automatically. After rebuilding gold: `POST http://localhost:8001/admin/reload-gold` (or restart uvicorn if you run without `--reload`).

## MLflow (optional)

```powershell
python scripts/train_cf_svd.py --n-components 16
mlflow ui --backend-store-uri "sqlite:///mlflow.db" --host 127.0.0.1 --port 5000
```

## Cloud (S3 + optional Glue)

Same transform (`movies_clean_lib` / Glue script). Three ways to run silver:

| mode | compute | data | command |
|------|---------|------|---------|
| **local** | laptop | local disk | `python scripts/build_movies_clean.py` |
| **s3 from laptop** | laptop | S3 bronze→silver | `python scripts/build_movies_clean_s3.py` |
| **Glue** | AWS | S3 bronze→silver | `deploy` once, then `run_glue_…` |

```powershell
python scripts/upload_s3_sample.py          # bronze JSON + MovieLens CSVs (+ optional local silver snapshot)
python scripts/build_movies_clean_s3.py     # rebuild silver on S3, compute=local
python scripts/deploy_glue_movies_clean.py  # upload script, create/update Glue job
python scripts/run_glue_movies_clean.py     # start job, wait, sync parquet to local preview
```

Default bucket: `s3://cinefind-gorelik-us-east-1/cinefind/…`  
Env: `CINEFIND_S3_BUCKET`, `CINEFIND_S3_PREFIX`, `CINEFIND_GLUE_ROLE` (default `AWSGlueServiceRole-retail`).

**Airflow:** one DAG `cinefind_local` with a branch (not two DAGs).  
Default silver=local. Trigger conf `{"silver": "glue"}` or Variable `cinefind_silver_mode`.  
Glue branch needs AWS on the worker; for daily tests keep `local`.
