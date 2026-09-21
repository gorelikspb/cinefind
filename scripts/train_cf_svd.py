"""Train TruncatedSVD on MovieLens ratings; save pkl + log MLflow.

  python scripts/train_cf_svd.py
  python scripts/train_cf_svd.py --n-components 16
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collab_lib import load_ratings  # noqa: E402

MODEL_DIR = ROOT / "data" / "raw_private" / "models"
MODEL_PATH = MODEL_DIR / "cf_svd.pkl"
META_PATH = MODEL_DIR / "cf_svd_meta.json"
MLFLOW_DB = ROOT / "mlflow.db"
ARTIFACT_ROOT = ROOT / "mlartifacts"

DEFAULT_N_COMPONENTS = 32
RANDOM_STATE = 42
TEST_SIZE = 0.2


def build_matrix(ratings: pd.DataFrame):
    user_ids = sorted(ratings["userId"].unique())
    movie_ids = sorted(ratings["movieId"].unique())
    u_index = {u: i for i, u in enumerate(user_ids)}
    m_index = {m: i for i, m in enumerate(movie_ids)}
    rows = ratings["userId"].map(u_index).to_numpy()
    cols = ratings["movieId"].map(m_index).to_numpy()
    data = ratings["rating"].to_numpy(dtype=float)
    mat = sparse.csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(movie_ids)))
    return mat, u_index, m_index, movie_ids


def predict_pairs(user_factors, item_factors, u_index, m_index, pairs: pd.DataFrame) -> np.ndarray:
    preds = []
    for user_id, movie_id in zip(pairs["userId"], pairs["movieId"]):
        ui = u_index.get(int(user_id))
        mi = m_index.get(int(movie_id))
        if ui is None or mi is None:
            preds.append(np.nan)
        else:
            preds.append(float(user_factors[ui] @ item_factors[mi]))
    return np.asarray(preds, dtype=float)


def main(n_components: int = DEFAULT_N_COMPONENTS) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB.resolve().as_posix()}")
    mlflow.set_experiment("cinefind_cf_svd")

    ratings = load_ratings()
    train_df, test_df = train_test_split(ratings, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    train_mat, u_index, m_index, movie_ids = build_matrix(train_df)
    n_comp = min(n_components, train_mat.shape[0] - 1, train_mat.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=RANDOM_STATE)
    user_factors = svd.fit_transform(train_mat)
    item_factors = svd.components_.T

    test_known = test_df[test_df["userId"].isin(u_index) & test_df["movieId"].isin(m_index)]
    preds = predict_pairs(user_factors, item_factors, u_index, m_index, test_known)
    mask = ~np.isnan(preds)
    rmse = float(np.sqrt(mean_squared_error(test_known.loc[mask, "rating"], preds[mask])))

    artifact = {
        "svd": svd,
        "user_factors": user_factors,
        "item_factors": item_factors,
        "u_index": u_index,
        "m_index": m_index,
        "movie_ids": list(movie_ids),
        "n_components": n_comp,
    }
    with MODEL_PATH.open("wb") as f:
        pickle.dump(artifact, f)

    meta = {
        "n_components": n_comp,
        "rmse_holdout": rmse,
        "n_train": int(len(train_df)),
        "n_test_scored": int(mask.sum()),
        "model_path": str(MODEL_PATH.relative_to(ROOT)).replace("\\", "/"),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    with mlflow.start_run(run_name=f"cf_svd_k{n_comp}"):
        mlflow.log_param("n_components", n_comp)
        mlflow.log_param("test_size", TEST_SIZE)
        mlflow.log_param("algorithm", "sklearn.TruncatedSVD")
        mlflow.log_metric("rmse_holdout", rmse)
        mlflow.log_metric("n_train", len(train_df))
        mlflow.log_artifact(str(MODEL_PATH))
        mlflow.log_artifact(str(META_PATH))
        run_id = mlflow.active_run().info.run_id

    print(f"n_components={n_comp}  holdout RMSE={rmse:.4f}  scored_test={int(mask.sum())}")
    print(f"wrote {MODEL_PATH}")
    print(f"mlflow run_id={run_id}  tracking=sqlite:///{MLFLOW_DB.name}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n-components", type=int, default=DEFAULT_N_COMPONENTS)
    main(n_components=p.parse_args().n_components)
