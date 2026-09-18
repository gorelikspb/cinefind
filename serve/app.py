"""Serve layer: demo profile recommendations as JSON + HTML poster cards.

Run from repo root:
  python -m uvicorn serve.app:app --reload --port 8001
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
SERVE_DIR = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from scoring_lib import DEMO_PROFILES, load_movies, score_profile  # noqa: E402

app = FastAPI(
    title="CineFind demo API",
    description="Serve gold-style top-N for fixed demo profiles (rules scorer).",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=SERVE_DIR / "static"), name="static")


def movies():
    """Load movies_clean.parquet; 503 if missing."""
    try:
        return load_movies()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


def get_payload(profile_id: str, top_n: int = 10) -> dict:
    """Validate inputs, run scorer, return JSON-shaped dict."""
    profile = DEMO_PROFILES.get(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"unknown profile_id; try: {', '.join(DEMO_PROFILES)}",
        )
    if top_n < 1 or top_n > 50:
        raise HTTPException(status_code=400, detail="top_n must be 1..50")
    try:
        return score_profile(movies(), profile, top_n=top_n)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def page(title: str, body: str) -> str:
    """Full HTML document shell + link to /static/demo.css."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="/static/demo.css">
</head>
<body><main>{body}</main></body></html>"""


def poster_block(url: object, title: str, href: object = None) -> str:
    """Poster <img> or placeholder; optional link to TMDb."""
    t = html.escape(str(title))
    if url:
        img = f'<img class="poster" src="{html.escape(str(url))}" alt="{t}" loading="lazy">'
    else:
        img = f'<div class="poster-fallback">No poster<br>{t}</div>'
    if href:
        return (
            f'<a class="poster-link" href="{html.escape(str(href))}" '
            f'target="_blank" rel="noopener">{img}</a>'
        )
    return img


def seed_titles(df, seed_ids: tuple[int, ...]) -> list[str]:
    """Titles for seed ids, in profile order."""
    by_id = {
        int(r.tmdb_id): str(r.title)
        for r in df[df["tmdb_id"].isin(seed_ids)].itertuples()
    }
    return [by_id.get(i, f"tmdb:{i}") for i in seed_ids]


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    """Landing: demo profiles with seeds + mood."""
    df = movies()
    cards = []
    for p in DEMO_PROFILES.values():
        titles = seed_titles(df, p.seed_tmdb_ids)
        seeds_html = "".join(f"<li>{html.escape(t)}</li>" for t in titles)
        cards.append(
            f"""<article class="profile-card">
  <h2><a href="/ui/{p.profile_id}">{html.escape(p.label)}</a></h2>
  <div class="muted"><code>{html.escape(p.profile_id)}</code> · mood: <strong>{html.escape(p.mood or '(none)')}</strong></div>
  <div class="muted" style="margin-top:0.55rem;">User seeds</div>
  <ol class="seed-list">{seeds_html}</ol>
  <div><a href="/ui/{p.profile_id}">Open top-10</a>
   · <a href="/v1/recommendations/{p.profile_id}">JSON</a></div>
</article>"""
        )
    body = f"""
  <h1>CineFind demo</h1>
  <p class="muted">Three demo profiles. Local catalog is still small, so top-10 picks are limited. Scorer runs on each request against <code>movies_clean</code>.</p>
  <div class="home-grid">{''.join(cards)}</div>
  <p class="muted"><a href="/docs">OpenAPI /docs</a> · <a href="/v1/profiles">/v1/profiles</a></p>
"""
    return page("CineFind demo", body)


@app.get("/ui/{profile_id}", response_class=HTMLResponse)
def ui_recommendations(profile_id: str, top_n: int = 10) -> str:
    """HTML top-10 for one profile (path param + optional ?top_n=)."""
    payload = get_payload(profile_id, top_n=top_n)
    seed_cards = "".join(
        f'<article class="seed">{poster_block(s.get("poster_url"), s["title"], s.get("tmdb_url"))}'
        f'<div class="meta">'
        f'<div class="title"><a href="{html.escape(str(s.get("tmdb_url") or "#"))}" target="_blank" rel="noopener">'
        f'{html.escape(str(s["title"]))}</a></div>'
        f'<div class="tmdb"><a href="{html.escape(str(s.get("tmdb_url") or "#"))}" target="_blank" rel="noopener">TMDb</a></div>'
        f"</div></article>"
        for s in payload["seeds"]
    )
    cards = "".join(
        f'<article class="card">{poster_block(r.get("poster_url"), r["title"], r.get("tmdb_url"))}'
        f'<div class="meta">'
        f'<div class="rank">#{r["rank"]}</div>'
        f'<div class="title"><a href="{html.escape(str(r.get("tmdb_url") or "#"))}" target="_blank" rel="noopener">'
        f'{html.escape(str(r["title"]))}</a></div>'
        f'<div class="genres">{html.escape(str(r.get("genres") or ""))}</div>'
        f'<div class="score">{r["score"]}</div>'
        f'<div class="reason">{html.escape(str(r["reason"]))}</div>'
        f'<div class="tmdb"><a href="{html.escape(str(r.get("tmdb_url") or "#"))}" target="_blank" rel="noopener">Open on TMDb</a></div>'
        f"</div></article>"
        for r in payload["results"]
    )
    body = f"""
  <p><a href="/">← profiles</a></p>
  <h1>{html.escape(payload['label'])}</h1>
  <p class="muted"><code>{html.escape(payload['profile_id'])}</code> · mood: {html.escape(payload['mood'] or '(none)')}</p>
  <h2 style="font-size:1rem;margin:1.25rem 0 0.35rem;">Seeds</h2>
  <div class="seed-row">{seed_cards}</div>
  <h2 style="font-size:1rem;margin:0.5rem 0 0.35rem;">Top {len(payload['results'])}</h2>
  <div class="grid">{cards}</div>
  <p class="muted"><a href="/v1/recommendations/{html.escape(profile_id)}">same as JSON</a></p>
"""
    return page(payload["label"], body)


@app.get("/health")
def health() -> dict:
    path_ok = (ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet").exists()
    return {"status": "ok" if path_ok else "degraded", "movies_clean": path_ok}


@app.get("/v1/profiles")
def list_profiles() -> dict:
    return {
        "profiles": [
            {
                "profile_id": p.profile_id,
                "label": p.label,
                "mood": p.mood,
                "seed_tmdb_ids": list(p.seed_tmdb_ids),
            }
            for p in DEMO_PROFILES.values()
        ]
    }


@app.get("/v1/recommendations/{profile_id}")
def recommendations(profile_id: str, top_n: int = 10) -> dict:
    """Same payload as /ui/{profile_id}, as JSON."""
    return get_payload(profile_id, top_n=top_n)
