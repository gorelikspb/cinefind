# CineFind

Capstone: movie picks from seed titles (+ mood). **Main story = data pipeline** (bronze → silver → gold → serve). Scoring is a thin demo layer with swappable channels — not a polished recommender.

## Docs

- `docs/progress.md` — status
- `architecture.md` — layers
- `docs/scoring.md` — score channels (content / collab / sklearn SVD / HF stub)
- `runbook.md` — local commands
- `notebooks/01_movielens_playground.ipynb` — quick look at MovieLens tables we use

## Local

```text
pip install -r requirements.txt
python scripts/build_movies_clean.py
python scripts/check_movies_dq.py
python scripts/score_demo_profile.py
python -m uvicorn serve.app:app --reload --port 8001
```

http://127.0.0.1:8001/
