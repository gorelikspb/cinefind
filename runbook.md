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

Airflow (`airflow/`): `build_movies_clean` → `check_movies_dq` → `score_demo_profile`.  
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
