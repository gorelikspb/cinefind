# CineFind progress

Short note for me and for whoever is coaching. Comment if something looks off.

## Idea

Help pick a movie from a few titles someone already likes, maybe with a mood. Capstone focus is the data pipeline and a small demo.

## Sources for now

TMDb for movie info. MovieLens for ratings and tags (it has links to TMDb ids). I also looked at https://app.trakt.tv/; maybe later for trending.

## Pipeline (rough)

Get raw data in. Clean into a movie table. Build features. Score a short list for a couple of demo profiles. Show it somehow (table, Metabase, or a tiny API later).

First scoring will stay simple and explainable. Embeddings can come after that works.

## Done

- Repo with README and this note
- Direction locked: seed movies + mood, TMDb + MovieLens

## Doing / next

- Get TMDb access and a MovieLens sample
- Pull a  metadata sample
- Make a  clean movie table preview
- A demo profile with a first top-10 from simple scoring

## Questions

Is TMDb + MovieLens ok as the starting pair?

Anything you’d change in the scope before I dig into the sample data?
