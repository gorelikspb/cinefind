# Runbook (local)

From repo root `cinefind/`. Needs `.env` with `TMDB_API_KEY`, venv with `requirements.txt`, MovieLens under `data/raw_private/movielens/`.

## Fetch (bronze)

```powershell
python scripts/fetch_tmdb_movies.py
```

Writes JSON to `data/raw_private/tmdb/movies/`. Retries on flaky network. Skip if file exists. `N` in the script = how many.

## Airflow (orchestrate build → DQ → score)

```powershell
cd airflow
docker compose up -d --pull never
```

UI: http://localhost:8080 — `airflow` / `airflow`  
DAG `cinefind_local`: unpause → Trigger.

```powershell
docker compose down
```

Fetch is **not** in the DAG. Manual pipeline without Airflow:

```powershell
cd scripts
python build_movies_clean.py
python check_movies_dq.py
python score_demo_profile.py
```

## Serve

```powershell
python -m uvicorn serve.app:app --reload --port 8001
```

http://localhost:8001 — needs `movies_clean` already built.
