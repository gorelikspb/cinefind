"""Serve: read gold profile_scores, mix channel weights, show top-N.

  python -m uvicorn serve.app:app --reload --port 8001
"""

from __future__ import annotations

import html
import sys
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scoring_lib import DEMO_PROFILES, load_movies, load_profile_scores, score_profile  # noqa: E402

app = FastAPI(title="CineFind demo", version="0.3.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@lru_cache(maxsize=1)
def _movies():
    return load_movies()


@lru_cache(maxsize=1)
def _gold():
    return load_profile_scores()


def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="/static/demo.css"></head>
<body><main>{body}</main></body></html>"""


def poster_block(url, title, href=None) -> str:
    t = html.escape(str(title))
    img = (
        f'<img class="poster" src="{html.escape(str(url))}" alt="{t}" loading="lazy">'
        if url
        else f'<div class="poster-fallback">No poster<br>{t}</div>'
    )
    if href:
        return f'<a class="poster-link" href="{html.escape(str(href))}" target="_blank" rel="noopener">{img}</a>'
    return img


def get_payload(profile_id: str, top_n: int, weights: dict) -> dict:
    profile = DEMO_PROFILES.get(profile_id)
    if profile is None:
        raise HTTPException(404, f"unknown profile; try {list(DEMO_PROFILES)}")
    return score_profile(_movies(), profile, top_n=top_n, gold=_gold(), **weights)


def weights_form(profile_id: str, w: dict, top_n: int) -> str:
    sliders = ""
    for key, param in (
        ("content", "w_content"),
        ("mood", "w_mood"),
        ("collab_n", "w_collab_n"),
        ("collab_avg", "w_collab_avg"),
        ("ml", "w_ml"),
        ("hf", "w_hf"),
    ):
        val = w.get(key, 0)
        sliders += f"""<label>{key} <input type="range" name="{param}" min="0" max="3" step="0.1"
          value="{val}" oninput="this.nextElementSibling.value=this.value">
          <output>{val}</output></label>"""
    return f"""<form class="weights" method="get" action="/ui/{html.escape(profile_id)}">
  <input type="hidden" name="top_n" value="{top_n}">{sliders}
  <button type="submit">Apply</button>
  <span class="muted">Gold channels; hf stub=0 until HF wired. See docs/scoring.md</span>
</form>"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    df = _movies()
    cards = []
    for p in DEMO_PROFILES.values():
        by_id = {int(r.tmdb_id): str(r.title) for r in df[df.tmdb_id.isin(p.seed_tmdb_ids)].itertuples()}
        seeds = "".join(f"<li>{html.escape(by_id.get(i, str(i)))}</li>" for i in p.seed_tmdb_ids)
        cards.append(
            f"""<article class="profile-card">
  <h2><a href="/ui/{p.profile_id}">{html.escape(p.label)}</a></h2>
  <div class="muted"><code>{p.profile_id}</code> · mood: {html.escape(p.mood)}</div>
  <ol class="seed-list">{seeds}</ol>
  <a href="/ui/{p.profile_id}">top-10 + sliders</a>
</article>"""
        )
    return page(
        "CineFind",
        f"<h1>CineFind demo</h1>"
        f"<p class='muted'>Pipeline gold → mix content / collab / ml / hf. Not a perfect recommender.</p>"
        f"<div class='home-grid'>{''.join(cards)}</div>",
    )


@app.get("/ui/{profile_id}", response_class=HTMLResponse)
def ui(
    profile_id: str,
    top_n: int = 10,
    w_content: float = Query(1.0),
    w_mood: float = Query(1.0),
    w_collab_n: float = Query(1.0),
    w_collab_avg: float = Query(1.0),
    w_ml: float = Query(0.0),
    w_hf: float = Query(0.0),
) -> str:
    weights = dict(
        w_content=w_content,
        w_mood=w_mood,
        w_collab_n=w_collab_n,
        w_collab_avg=w_collab_avg,
        w_ml=w_ml,
        w_hf=w_hf,
    )
    payload = get_payload(profile_id, top_n, weights)
    seed_cards = "".join(
        f'<article class="seed">{poster_block(s.get("poster_url"), s["title"], s.get("tmdb_url"))}'
        f'<div class="meta"><div class="title">{html.escape(str(s["title"]))}</div></div></article>'
        for s in payload["seeds"]
    )
    cards = "".join(
        f'<article class="card">{poster_block(r.get("poster_url"), r["title"], r.get("tmdb_url"))}'
        f'<div class="meta"><div class="rank">#{r["rank"]}</div>'
        f'<div class="title">{html.escape(str(r["title"]))}</div>'
        f'<div class="genres">{html.escape(str(r.get("genres") or ""))}</div>'
        f'<div class="score">final {r["score"]}</div>'
        f'<div class="channels muted">c {r["content_score"]} · mood {r["mood_score"]} · '
        f'n {r["collab_n"]} · avg {r["collab_avg"]} · ml {r["ml_score"]} · hf {r["hf_score"]}</div>'
        f'<div class="reason">{html.escape(r["reason"])}</div></div></article>'
        for r in payload["results"]
    )
    return page(
        payload["label"],
        f'<p><a href="/">← profiles</a></p>'
        f'<h1>{html.escape(payload["label"])}</h1>'
        f'<p class="muted">neighbor pool: {payload.get("neighbor_pool")}</p>'
        f'{weights_form(profile_id, payload["weights"], top_n)}'
        f'<h2 style="font-size:1rem">Seeds</h2><div class="seed-row">{seed_cards}</div>'
        f'<h2 style="font-size:1rem">Top {len(payload["results"])}</h2><div class="grid">{cards}</div>',
    )


@app.get("/health")
def health():
    return {
        "movies_clean": (ROOT / "data/raw_private/preview/movies_clean.parquet").exists(),
        "profile_scores": (ROOT / "data/raw_private/preview/profile_scores.parquet").exists(),
    }


@app.get("/v1/profiles")
def profiles():
    return {
        "profiles": [
            {"profile_id": p.profile_id, "label": p.label, "mood": p.mood, "seed_tmdb_ids": list(p.seed_tmdb_ids)}
            for p in DEMO_PROFILES.values()
        ]
    }


@app.get("/v1/recommendations/{profile_id}")
def recommendations(
    profile_id: str,
    top_n: int = 10,
    w_content: float = 1.0,
    w_mood: float = 1.0,
    w_collab_n: float = 1.0,
    w_collab_avg: float = 1.0,
    w_ml: float = 0.0,
    w_hf: float = 0.0,
):
    return get_payload(
        profile_id,
        top_n,
        dict(
            w_content=w_content,
            w_mood=w_mood,
            w_collab_n=w_collab_n,
            w_collab_avg=w_collab_avg,
            w_ml=w_ml,
            w_hf=w_hf,
        ),
    )


@app.post("/admin/reload-gold")
def reload_gold():
    _movies.cache_clear()
    _gold.cache_clear()
    return {"rows": len(_gold())}
