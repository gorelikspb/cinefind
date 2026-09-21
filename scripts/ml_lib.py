"""Load sklearn SVD artifact and score candidates vs seed movieIds."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data" / "raw_private" / "models" / "cf_svd.pkl"


def load_cf_svd(path: Path = MODEL_PATH) -> dict:
    with path.open("rb") as f:
        return pickle.load(f)


def ml_scores_for_seeds(
    seed_movie_ids: list[int],
    allowed_movie_ids: set[int],
    model: dict | None = None,
) -> pd.DataFrame:
    model = load_cf_svd() if model is None else model
    m_index = model["m_index"]
    item_factors = model["item_factors"]

    seed_idx = [m_index[m] for m in seed_movie_ids if m in m_index]
    if not seed_idx:
        return pd.DataFrame(columns=["movieId", "ml_score"])

    seed_vec = item_factors[seed_idx].mean(axis=0)
    n = np.linalg.norm(seed_vec)
    if n > 0:
        seed_vec = seed_vec / n

    seed_set = set(int(x) for x in seed_movie_ids)
    rows = []
    for mid in allowed_movie_ids:
        mid = int(mid)
        if mid in seed_set or mid not in m_index:
            continue
        vec = item_factors[m_index[mid]]
        vn = np.linalg.norm(vec)
        if vn > 0:
            vec = vec / vn
        rows.append({"movieId": mid, "ml_score": float(seed_vec @ vec)})
    return pd.DataFrame(rows)
