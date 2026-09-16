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
- TMDb API key works (`test_tmdb_key.py` → OK)
- Fetch script for TMDb movies (retries; network sometimes drops)
- Pulled TMDb JSON locally: **47/50** saved (~6 min; a few failed on flaky network, can re-run)

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

- Run `python scripts/test_tmdb_key.py` (should print OK).
- Then pull movie info: `python scripts/fetch_tmdb_movies.py`  
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
