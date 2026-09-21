"""CineFind pipeline: silver → DQ → gold.

One DAG (not two). Conf / Variable picks silver backend:

  silver=local  (default) — disk build (daily tests)
  silver=glue             — Glue job then sync parquet locally for DQ/gold

UI Trigger conf: {"silver": "glue"}
Variable: cinefind_silver_mode = local|glue

Glue branch needs AWS creds on the Airflow worker (Docker often has none → use local).
"""

from __future__ import annotations

from datetime import datetime

from airflow.sdk import DAG

try:
    from airflow.sdk import Variable
except Exception:  # pragma: no cover
    from airflow.models import Variable

try:
    from airflow.providers.standard.operators.bash import BashOperator
    from airflow.providers.standard.operators.python import BranchPythonOperator
except ImportError:
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import BranchPythonOperator

SCRIPTS = "/opt/cinefind/scripts"


def pick_silver(**context) -> str:
    conf = (context.get("dag_run") and context["dag_run"].conf) or {}
    mode = conf.get("silver")
    if not mode:
        try:
            mode = Variable.get("cinefind_silver_mode", default="local")
        except TypeError:
            mode = Variable.get("cinefind_silver_mode", default_var="local")
        except Exception:
            mode = "local"
    if str(mode).lower() == "glue":
        return "build_movies_clean_glue"
    return "build_movies_clean_local"


with DAG(
    dag_id="cinefind_local",
    description="silver (local|glue) → DQ → gold",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["cinefind"],
    params={"silver": "local"},
) as dag:
    choose_silver = BranchPythonOperator(
        task_id="choose_silver",
        python_callable=pick_silver,
    )

    build_movies_clean_local = BashOperator(
        task_id="build_movies_clean_local",
        bash_command=f"cd {SCRIPTS} && python build_movies_clean.py",
    )

    build_movies_clean_glue = BashOperator(
        task_id="build_movies_clean_glue",
        bash_command=f"cd {SCRIPTS} && python run_glue_movies_clean.py",
    )

    check_movies_dq = BashOperator(
        task_id="check_movies_dq",
        bash_command=f"cd {SCRIPTS} && python check_movies_dq.py",
        trigger_rule="none_failed_min_one_success",
    )

    score_demo_profiles = BashOperator(
        task_id="score_demo_profiles",
        bash_command=f"cd {SCRIPTS} && python score_demo_profile.py",
    )

    choose_silver >> [build_movies_clean_local, build_movies_clean_glue]
    [build_movies_clean_local, build_movies_clean_glue] >> check_movies_dq >> score_demo_profiles
