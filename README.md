# CineFind

Small capstone project: recommend movies from a few titles you already like (and maybe a mood).

For now the point is the data pipeline and a simple demo, not a polished consumer app.

## Stack I’m aiming at

TMDb, MovieLens, then later S3 / Glue / Athena, Airflow, and something to show results (Metabase or a small FastAPI).

## Where things stand

See `docs/progress.md`. Draft sketch: `architecture.md`.

## Local demo API (optional)

Needs `movies_clean.parquet` from `scripts/build_movies_clean.py`.

```text
pip install -r requirements.txt
python -m uvicorn serve.app:app --reload --port 8001
```

Then open http://127.0.0.1:8001/ — profiles: `demo_family`, `demo_crime`, `demo_romance`.
