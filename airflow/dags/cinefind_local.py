"""Local CineFind pipeline: silver build → DQ → gold demo scores.

Trigger manually in the Airflow UI. Uses already-fetched TMDb JSON under data/.
Fetch stays a separate CLI step (network + API key).
"""

from __future__ import annotations

from datetime import datetime

from airflow.sdk import DAG

try:
    from airflow.providers.standard.operators.bash import BashOperator
except ImportError:  # Airflow 2.x fallback
    from airflow.operators.bash import BashOperator

SCRIPTS = "/opt/cinefind/scripts"

with DAG(
    dag_id="cinefind_local",
    description="build_movies_clean → check_movies_dq → score_demo_profile",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["cinefind", "local"],
) as dag:
    build_movies_clean = BashOperator(
        task_id="build_movies_clean",
        bash_command=f"cd {SCRIPTS} && python build_movies_clean.py",
    )

    check_movies_dq = BashOperator(
        task_id="check_movies_dq",
        bash_command=f"cd {SCRIPTS} && python check_movies_dq.py",
    )

    score_demo_profiles = BashOperator(
        task_id="score_demo_profiles",
        bash_command=f"cd {SCRIPTS} && python score_demo_profile.py",
    )

    build_movies_clean >> check_movies_dq >> score_demo_profiles
