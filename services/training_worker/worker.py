import asyncio
import json
import os
import subprocess
import tempfile

import mlflow
from mlflow.tracking import MlflowClient

try:
    from db import (
        get_job,
        save_trained_model,
        update_status,
    )
    from minio_client import (
        download_dataset,
        save_model_to_minio,
    )
except ModuleNotFoundError:
    from .db import (
        get_job,
        save_trained_model,
        update_status,
    )
    from .minio_client import (
        download_dataset,
        save_model_to_minio,
    )

POLL_INTERVAL = 5
TMP_ROOT = os.getenv("WORKER_TMP_DIR", tempfile.gettempdir())


async def worker_loop():
    import logging
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
    logging.info("WORKER LOOP STARTED")
    while True:
        try:
            job = await get_job()
            logging.info(f"Polled, got job: {job}")

            if job:
                await process_job(job)
        except Exception as e:
            logging.error(f"Worker loop error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def process_job(job):
    import logging

    job_id = job["job_id"]
    dataset_name = job["dataset_name"]
    dataset_id = job["dataset_id"]
    import logging as log
    import shutil

    try:
        log.info(f"Processing job {job_id}: downloading dataset {dataset_name}")
        dataset_object_name = job.get("dataset_path") or dataset_name
        local_file_name = os.path.basename(dataset_object_name)
        data_path = os.path.join(TMP_ROOT, local_file_name)
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        log.info(f"Downloading to {data_path}")
        download_dataset(dataset_object_name, data_path)
        log.info(f"Dataset downloaded to {data_path}")
        csv_path = data_path if data_path.endswith(".csv") else f"{data_path}.csv"
        if csv_path != data_path:
            shutil.move(data_path, csv_path)
        log.info(f"Moved to {csv_path}")
        artifacts_dir = os.path.join(TMP_ROOT, f"training_artifacts_{job_id}")
        result = subprocess.run(
            [
                "python",
                "pipelines/first_ml_baseline/train.py",
                "--data",
                csv_path,
                "--job_id",
                str(job_id),
                "--artifacts-dir",
                artifacts_dir,
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "/app"},
        )
        log.info(
            f"Pipeline stdout: {result.stdout[:500] if result.stdout else 'empty'}"
        )
        if result.stderr:
            log.warning(f"Pipeline stderr: {result.stderr[:500]}")

        if result.returncode != 0:
            raise Exception(f"Pipeline failed: {result.stderr}")

        client = MlflowClient()

        # Here we find the experiment by job_id and the latest job
        experiment_name = "first_ml_baseline"
        exp = mlflow.get_experiment_by_name(experiment_name)

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            max_results=100,
            order_by=["attributes.start_time DESC"],
        )
        runs = [r for r in runs if r.data.tags.get("job_id") == str(job_id)]

        if not runs:
            raise Exception("MLflow run not found for job_id")

        # Get information from MLflow
        run = runs[0]
        run_id = run.info.run_id

        params = dict(run.data.params)
        metrics = run.data.metrics
        model_name = run.data.params["model_type"]
        reference_profile_path = os.path.join(artifacts_dir, "reference_profile.json")
        if os.path.exists(reference_profile_path):
            with open(reference_profile_path, "r", encoding="utf-8") as file:
                params["reference_profile"] = json.load(file)

        local_model_path = os.path.join(artifacts_dir, "model.joblib")

        # Model version creating
        model_version = f"{job_id}_{dataset_id}_{run_id}"
        log.info(f"Model version: {model_version}")

        # Update status to mark the code part of saving model artifacts
        log.info("Updating status to persisting")
        await update_status(job_id, "persisting")
        log.info("Downloading artifacts from MLflow")

        model_path = save_model_to_minio(
            local_model_path=local_model_path,
            model_name=model_name,
            model_version=model_version,
        )

        await save_trained_model(
            job_id=job_id,
            model_name=model_name,
            model_version=model_version,
            model_path=model_path,
            metrics=metrics,
            parameters=params,
        )

        await update_status(job_id, "succeeded")

    except Exception as e:
        import logging

        logging.error(f"Error processing job {job_id}: {e}", exc_info=True)
        try:
            await update_status(job_id, "failed")
        except Exception as update_err:
            logging.error(f"Failed to update status: {update_err}")
        # DO NOT re-raise the exception. Let the worker continue to the next job.
