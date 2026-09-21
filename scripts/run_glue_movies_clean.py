"""Start Glue job cinefind_build_movies_clean and wait for SUCCESS/FAILED.

After SUCCESS, downloads silver parquet to local preview so DQ/gold can run.

  python scripts/run_glue_movies_clean.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
JOB_NAME = os.environ.get("CINEFIND_GLUE_JOB", "cinefind_build_movies_clean")
BUCKET = os.environ.get("CINEFIND_S3_BUCKET", "cinefind-gorelik-us-east-1")
PREFIX = os.environ.get("CINEFIND_S3_PREFIX", "cinefind").strip("/")
LOCAL_CLEAN = ROOT / "data" / "raw_private" / "preview" / "movies_clean.parquet"


def main() -> None:
    glue = boto3.client("glue")
    s3 = boto3.client("s3")
    resp = glue.start_job_run(
        JobName=JOB_NAME,
        Arguments={"--BUCKET": BUCKET, "--PREFIX": PREFIX},
    )
    run_id = resp["JobRunId"]
    print(f"started {JOB_NAME} run_id={run_id}")
    while True:
        run = glue.get_job_run(JobName=JOB_NAME, RunId=run_id)["JobRun"]
        state = run["JobRunState"]
        print(f"  state={state}")
        if state in ("SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT", "ERROR"):
            if state != "SUCCEEDED":
                raise SystemExit(run.get("ErrorMessage") or state)
            silver_key = f"{PREFIX}/silver/movies_clean.parquet"
            LOCAL_CLEAN.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(BUCKET, silver_key, str(LOCAL_CLEAN))
            print(f"ok s3://{BUCKET}/{silver_key}")
            print(f"synced local {LOCAL_CLEAN}")
            return
        time.sleep(10)


if __name__ == "__main__":
    main()
