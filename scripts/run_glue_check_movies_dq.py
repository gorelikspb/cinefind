"""Start Glue DQ job cinefind_check_movies_dq and wait for SUCCESS/FAILED.

  python scripts/run_glue_check_movies_dq.py
"""

from __future__ import annotations

import os
import time

import boto3

JOB_NAME = os.environ.get("CINEFIND_GLUE_DQ_JOB", "cinefind_check_movies_dq")
BUCKET = os.environ.get("CINEFIND_S3_BUCKET", "cinefind-gorelik-us-east-1")
PREFIX = os.environ.get("CINEFIND_S3_PREFIX", "cinefind").strip("/")


def main() -> None:
    glue = boto3.client("glue")
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
            print(f"DQ ok on s3://{BUCKET}/{PREFIX}/silver/movies_clean.parquet")
            return
        time.sleep(10)


if __name__ == "__main__":
    main()
