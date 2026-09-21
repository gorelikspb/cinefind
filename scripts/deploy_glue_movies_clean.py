"""Upload Glue script to S3 and create/update Glue Python Shell job.

  python scripts/deploy_glue_movies_clean.py
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
BUCKET = os.environ.get("CINEFIND_S3_BUCKET", "cinefind-gorelik-us-east-1")
PREFIX = os.environ.get("CINEFIND_S3_PREFIX", "cinefind").strip("/")
JOB_NAME = os.environ.get("CINEFIND_GLUE_JOB", "cinefind_build_movies_clean")
ROLE = os.environ.get("CINEFIND_GLUE_ROLE", "AWSGlueServiceRole-retail")
SCRIPT_LOCAL = ROOT / "glue" / "build_movies_clean.py"
# Glue role already reads the account glue-assets bucket; data stays on CINEFIND bucket.
ASSETS_BUCKET = os.environ.get(
    "CINEFIND_GLUE_ASSETS_BUCKET", "aws-glue-assets-293162038858-us-east-1"
)
SCRIPT_KEY = "cinefind/build_movies_clean.py"


def main() -> None:
    s3 = boto3.client("s3")
    glue = boto3.client("glue")
    s3.upload_file(str(SCRIPT_LOCAL), ASSETS_BUCKET, SCRIPT_KEY)
    script_uri = f"s3://{ASSETS_BUCKET}/{SCRIPT_KEY}"
    print(f"script -> {script_uri}")

    command = {
        "Name": "pythonshell",
        "PythonVersion": "3.9",
        "ScriptLocation": script_uri,
    }
    default_args = {
        "--BUCKET": BUCKET,
        "--PREFIX": PREFIX,
        "--job-language": "python",
    }
    try:
        glue.get_job(JobName=JOB_NAME)
        glue.update_job(
            JobName=JOB_NAME,
            JobUpdate={
                "Role": ROLE,
                "Command": command,
                "DefaultArguments": default_args,
                "MaxCapacity": 0.0625,
                "GlueVersion": "3.0",
            },
        )
        print(f"updated Glue job {JOB_NAME}")
    except glue.exceptions.EntityNotFoundException:
        glue.create_job(
            Name=JOB_NAME,
            Role=ROLE,
            Command=command,
            DefaultArguments=default_args,
            MaxCapacity=0.0625,
            GlueVersion="3.0",
        )
        print(f"created Glue job {JOB_NAME}")


if __name__ == "__main__":
    main()
