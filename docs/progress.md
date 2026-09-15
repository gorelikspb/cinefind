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
