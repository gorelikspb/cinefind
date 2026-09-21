# CineFind progress

Short note for me and for whoever is coaching. Comment if something looks off.

## Idea

Help pick a movie from a few titles someone already likes, maybe with a mood. Capstone focus is the data pipeline and a demo.

## Sources for now

TMDb for movie info. MovieLens for ratings and tags (it has links to TMDb ids). I also looked at https://app.trakt.tv/; maybe later for trending.

## Pipeline (rough)

Get raw data in. Clean into a movie table. Build features. Score a short list for a couple of demo profiles. Show it somehow (table, Metabase, or an API later).

First scoring will stay simple and explainable. Embeddings can come after that works.

## Done

- Repo with README and this note
- Direction locked: seed movies + mood, TMDb + MovieLens
- GitHub Project board for tasks
- MovieLens `ml-latest-small` downloaded locally
- TMDb API key works (local `.env`)
- Fetch script for TMDb movies (retries; network sometimes drops)
- Pulled TMDb JSON locally: **47/50** saved (~6 min; a few failed on flaky network, can re-run)
- Local cleaned movie table preview (`movies_clean` CSV + Parquet): TMDb fields + MovieLens id join; 47/47 matched
- Demo profile → rules-based top-10 with reasons (`demo_top10.csv`)
- First DQ script on `movies_clean` / raw presence (`check_movies_dq.py`)
- Architecture sketch + pipeline diagram in the repo
- FastAPI serve demo (`serve/app.py`): HTML cards + JSON; scorer runs per request on `movies_clean`
- Three demo profiles (`demo_family`, `demo_crime`, `demo_romance`) in `scoring_lib`
- `movies_clean` keeps TMDb `poster_path`; UI shows posters + TMDb links
- Local catalog is still small (~50 movies), so demo recommendations are limited
- Dropped obsolete `test_tmdb_key.py`
- Local Airflow (Docker Compose under `airflow/`): DAG `cinefind_local` = build → DQ → score; one manual run succeeded (~20s). UI localhost:8080 (airflow/airflow). Fetch still CLI.
- Local `runbook.md`: fetch / Airflow / serve commands
- Widened TMDb pull: target 250, **232/250** saved (~235 JSON on disk); network still drops some ids
- Rebuilt `movies_clean` (235 rows, join 100%) + DQ pass + demo top-10 after widen
- Airflow re-run on widened catalog: DAG `cinefind_local` **success** (build → DQ → score); verified via `dags list-runs` / `tasks states-for-dag-run` + parquet 235 rows + top10 CSV mtimes
- Gold `profile_scores` + serve sliders; channels: content, collab (pandas), ml (sklearn SVD + MLflow), hf (stub plug-in). Details: `docs/scoring.md`.
- Widen TMDb fetch target **500** (first N `tmdbId` from MovieLens `links.csv`); **485** JSON on disk → `movies_clean` 485 + DQ pass + gold rebuild.
- S3 sample land: bucket `cinefind-gorelik-us-east-1`, script `upload_s3_sample.py` (bronze JSON + silver parquet under `cinefind/`).

## Questions

Is TMDb + MovieLens ok as the starting pair?

Anything you’d change in the scope before I dig into the sample data?

## Next step

Trying local data first (no S3 yet).

- Download MovieLens (`ml-latest-small`) from https://files.grouplens.org/datasets/movielens/ml-latest-small.zip and look through it: row counts, nulls, how links map movieId → tmdbId.
- Put TMDb API key aside, pull movie info, check which fields we need (title, genres, overview, keywords…).
- Then make a cleaned movie table preview and one demo profile → top-10 with simple scoring.

## MovieLens notes (local)

Downloaded `ml-latest-small` (kept out of git).

Quick look:

- `movies` — 9,742 movies (id, title, genres)
- `ratings` — 100,836 ratings from 610 users (0.5–5.0, mean ~3.50)
- `tags` — 3,683 tag rows
- `links` — movieId → imdbId / tmdbId; **8 movies missing tmdbId**
- genres are pipe-separated (`Action|Comedy|…`)

Playaround notebook is in the repo.

## Next step

- Open the notebook and poke at the tables (joins to tmdbId, genres, a few titles).
- Then TMDb: API key, pull movie info locally.
- After that: cleaned movie table preview + one demo profile → top-10.

## TMDb notes

API key lives in local `.env` (not in git).

Rate limit: roughly ~40 requests/sec soft cap; if you get HTTP 429, wait and retry. We just sleep a bit between calls.

Docs: https://developer.themoviedb.org/docs/rate-limiting

## Next step

- Confirm TMDb key in local `.env`, then pull movie info: `python scripts/fetch_tmdb_movies.py`  
  Default is **3** movies (network to TMDb is flaky; script retries). Bump `N` in the script later when it feels stable.
- Open a few JSON files / poke in a notebook, then cleaned movie table preview.

## Next step

- Finish / check the local TMDb pull (aim ~50 movies).
- Look at a few JSON fields we need, then build a cleaned movie table preview (join with MovieLens).
- After that: one demo profile → top-10 with simple scoring.

## Network note (TMDb from home)

Some HTTPS calls to TMDb drop mid-handshake (`connection reset`). Key is fine — looks like the local path (Wi‑Fi / ISP / VPN / antivirus), not the API itself. Script retries and continues.

Impact on the project: low for now. Local samples still work; on a stable network or later in the cloud this should be quieter. Not a reason to redesign the pipeline.

OMDb? Possible backup (IMDb-oriented), but free tier is tighter and metadata is thinner than TMDb. I’d keep TMDb as main source unless coaches push otherwise.

## Next step

- Keep local field pick → cleaned movie table → demo top-10.
- Draft docs (sketches): `architecture.md` (pipeline) + `runbook.md` (run/fail). Include raw checks, DQ in the pipeline, silver as Parquet, small debug volumes vs later scale.
- Cloud later, same layers: **S3+Glue+Athena+Airflow**, or **ADLS+Databricks/PySpark/Delta**.

## Next step

- Orchestrate the existing scripts (Airflow / Jobs) in layer order.
- Later: widen the movie sample so recommendations have more room; collaborative ratings; cloud small-batch; `runbook.md` when ops steps are stable.

## Next step

Local Airflow (Docker Compose under `airflow/`):

- `docker compose up -d` from `airflow/`
- UI `http://localhost:8080` — login `airflow` / `airflow`
- Unpause DAG `cinefind_local`, Trigger → build → DQ → score
- Fetch TMDb stays CLI for now (API key + flaky network)

## Scoring notes (now vs later)

**Now (rough engine):** content rules on `movies_clean` — shared genres/keywords, optional mood word, TMDb `vote_average` as a light quality nudge. Enough to show the pipeline end-to-end.

**Later (use MovieLens ratings we already have, but do not wire in yet):**
- Do not rely only on a global average score.
- Idea: find people who rated the seed movies similarly (close taste), then recommend titles **those** people liked and the user has not seeded.
- That needs enough overlapping ratings (MovieLens `ratings` is built for this: many users × many movies). Our `ml-latest-small` is already a starting point; bigger dumps (20M/32M) give denser neighborhoods.
- Still keep a content/fallback path when overlap is thin.

Until then: keep the crude scorer; ratings stay unused bronze/silver candidates.

## Scale note (keep simple)

- **Ratings** can grow from MovieLens **files** (100k → 20M/32M). No API.
- **Movie info** via TMDb API is fine for a **small/local** catalog. Huge pulls hit rate limits / ToS risk — not the path for “all movies”.
- Capstone stays simple: local sample + pipeline; scoring channels are demos you can swap.

## Next step

Cloud: rebuild silver **from bronze on S3** (Glue / Databricks / same Python on EMR), then DQ + gold paths. Local widen/re-fetch gaps ok as needed. Scoring stays plug-in for subjective demos.
