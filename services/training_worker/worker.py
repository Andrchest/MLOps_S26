import asyncio
import subprocess
import mlflow
import os
from mlflow.tracking import MlflowClient
from services.training_worker.db import (
    get_job,
    recover_stuck_jobs,
    update_status,
    save_trained_model,
    JobStatus,
)
from services.training_worker.minio_client import (
    download_dataset,
    save_model_to_minio,
)
from services.training_worker.retry import (
    sync_retry,
    async_retry,
)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 5))
TMP_DIR = os.getenv("TMP_DIR", "/tmp")
TRAINING_SCRIPT = os.getenv("TRAINING_SCRIPT", "pipelines/first_ml_baseline/train.py")
TIMEOUT = int(os.getenv("TRAINING_TIMEOUT", 300))


async def worker_loop():
    import logging
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
    logging.info("WORKER LOOP STARTED")

    # Updates status for "running" jobs
    await recover_stuck_jobs()

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
    job_id = job["job_id"]
    dataset_name = job["dataset_name"]
    dataset_id = job["dataset_id"]
    import logging as log
    import shutil

    try:
        log.info(f"Processing job {job_id}: downloading dataset {dataset_name}")
        data_path = os.path.join(TMP_DIR, dataset_name)
        os.makedirs("/tmp", exist_ok=True)

        log.info(f"Downloading to {data_path}")
        sync_retry(download_dataset, dataset_name=dataset_name, file_path=data_path)
        log.info(f"Dataset downloaded to {data_path}")

        csv_path = f"{data_path}.csv"
        # Adds .csv to the dataset name
        shutil.move(data_path, csv_path)
        log.info(f"Moved to {csv_path}")
        # Own try/except for subprocess
        try:
            result = subprocess.run(
                [
                    "python",
                    TRAINING_SCRIPT,
                    "--data",
                    csv_path,
                    "--job_id",
                    str(job_id),
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise Exception("Training timeout")

        log.info(
            f"Pipeline stdout: {result.stdout[:500] if result.stdout else 'empty'}"
        )
        if result.stderr:
            log.warning(f"Pipeline stderr: {result.stderr[:500]}")

        if result.returncode != 0:
            raise Exception(f"Pipeline failed: {result.stderr}")

        client = MlflowClient()

        # Here we find the experiment by job_id and the latest job
        experiment_name = os.getenv("MLFLOW_EXPERIMENT", "first_ml_baseline")
        exp = mlflow.get_experiment_by_name(experiment_name)

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string=f"tags.job_id = '{job_id}'",
            max_results=1,
            order_by=["attributes.start_time DESC"],
        )

        if not runs:
            raise Exception("MLflow run not found for job_id")

        # Get information from MLflow
        run = runs[0]
        run_id = run.info.run_id

        params = run.data.params
        metrics = run.data.metrics
        model_name = run.data.params["model_type"]

        # Model is already saved locally by the training pipeline
        local_model_path = "artifacts"

        # Model version creating
        model_version = f"{job_id}_{dataset_id}_{run_id}"
        log.info(f"Model version: {model_version}")

        # Update status to mark the code part of saving model artifacts
        log.info("Updating status to persisting")
        await async_retry(update_status, job_id, JobStatus.PERSISTING)
        log.info("Downloading artifacts from MLflow")

        model_path = sync_retry(
            save_model_to_minio,
            local_model_path=local_model_path,
            model_name=model_name,
            model_version=model_version,
        )

        await async_retry(
            save_trained_model,
            job_id=job_id,
            model_name=model_name,
            model_version=model_version,
            model_path=model_path,
            metrics=metrics,
            parameters=params,
        )

        await async_retry(update_status, job_id, JobStatus.SUCCEEDED)

    except Exception as e:
        import logging

        logging.error(f"Error processing job {job_id}: {e}", exc_info=True)
        try:
            await async_retry(update_status, job_id, JobStatus.FAILED)
        except Exception as update_err:
            logging.error(f"Failed to update status: {update_err}")
        # DO NOT re-raise the exception. Let the worker continue to the next job.
