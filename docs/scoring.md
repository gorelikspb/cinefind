# Scoring (demo channels)

Capstone focus is the **data pipeline**. Scoring here is a thin gold layer: several numeric columns per profile × movie, then serve mixes weights.

Not claiming a perfect recommender — these are **plug-in style** trials:

| column | idea | where |
|--------|------|--------|
| `content_score` | genre/keyword/vote overlap with seeds | `scoring_lib.score_row` |
| `mood_score` | 1 if mood word hits genres/keywords/overview/title | `scoring_lib.mood_score` |
| `collab_n` / `collab_avg` | pandas neighbors on MovieLens ratings | `collab_lib` |
| `ml_score` | sklearn TruncatedSVD on ratings | `train_cf_svd` → `ml_lib` |
| `hf_score` | Hugging Face text embeddings (overview) | stub in `build_profile_scores` — swap in a real model when needed |

Gold build: `scripts/build_profile_scores.py` / `score_demo_profile.py` → `profile_scores.parquet`.  
Serve: sliders on those columns.
