"""Shared TMDb JSON + MovieLens links → movies_clean DataFrame."""

from __future__ import annotations

import pandas as pd


def genres_str(data: dict) -> str:
    names = [g["name"] for g in data.get("genres") or [] if g.get("name")]
    return "|".join(names)


def keywords_str(data: dict) -> str:
    kws = (data.get("keywords") or {}).get("keywords") or []
    names = [k["name"] for k in kws if k.get("name")]
    return "|".join(names)


def row_from_tmdb(data: dict) -> dict:
    return {
        "tmdb_id": data.get("id"),
        "imdb_id": data.get("imdb_id"),
        "title": data.get("title") or data.get("original_title"),
        "original_title": data.get("original_title"),
        "overview": data.get("overview") or "",
        "genres": genres_str(data),
        "keywords": keywords_str(data),
        "release_date": data.get("release_date") or "",
        "runtime": data.get("runtime"),
        "original_language": data.get("original_language"),
        "popularity": data.get("popularity"),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "poster_path": data.get("poster_path") or "",
    }


def prepare_links(links: pd.DataFrame) -> pd.DataFrame:
    links = links.dropna(subset=["tmdbId"]).copy()
    links["tmdbId"] = links["tmdbId"].astype(int)
    return links.rename(
        columns={"movieId": "movielens_id", "tmdbId": "tmdb_id", "imdbId": "imdb_id_ml"}
    )


def prepare_ml_movies(ml_movies: pd.DataFrame) -> pd.DataFrame:
    return ml_movies.rename(
        columns={"movieId": "movielens_id", "title": "title_ml", "genres": "genres_ml"}
    )


def build_movies_clean(
    tmdb_rows: list[dict],
    links: pd.DataFrame,
    ml_movies: pd.DataFrame,
) -> pd.DataFrame:
    """Join TMDb flat rows with MovieLens ids/titles."""
    tmdb = pd.DataFrame(row_from_tmdb(r) for r in tmdb_rows)
    links = prepare_links(links)
    ml_movies = prepare_ml_movies(ml_movies)
    out = tmdb.merge(links[["movielens_id", "tmdb_id"]], on="tmdb_id", how="left")
    return out.merge(ml_movies, on="movielens_id", how="left")
