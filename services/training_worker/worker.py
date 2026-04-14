import asyncio
import subprocess
import mlflow
import os
from mlflow.tracking import MlflowClient
from db import (
    get_job,
    update_status,
    save_trained_model,
)
from minio_client import (
    download_dataset,
    save_model_to_minio,
)

POLL_INTERVAL = 5


async def worker_loop():
    while True:
        job = await get_job()

        if job:
            await process_job(job)

        await asyncio.sleep(POLL_INTERVAL)


async def process_job(job):
    job_id = job["job_id"]
    dataset_name = job["dataset_name"]
    dataset_id = job["dataset_id"]

    try:
        data_path = f"/tmp/{dataset_name}"
        os.makedirs("/tmp", exist_ok=True)
        download_dataset(dataset_name, data_path)

        # Starting of the pipeline
        result = subprocess.run(
            [
                "python",
                "pipelines/first_ml_baseline/train.py",
                "--data",
                data_path,
                "--job_id",
                str(job_id),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise Exception(f"Pipeline failed: {result.stderr}")

        client = MlflowClient()

        # Here we find the experiment by job_id and the latest job
        experiment_name = "first_ml_baseline"
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

        local_model_path = mlflow.artifacts.download_artifacts(
            artifact_uri=f"runs:/{run_id}/model"
        )

        # Model version creating
        model_version = f"{job_id}_{dataset_id}_{run_id}"

        # Update status to mark the code part of saving model artifacts
        await update_status(job_id, "persisting")

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
        print(f"Error processing job {job_id}: {e}")
        await update_status(job_id, "failed")
        # DO NOT re-raise the exception. Let the worker continue to the next job.
