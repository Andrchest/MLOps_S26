import asyncio
import subprocess
import mlflow
import shutil
import os
import logging
from mlflow.tracking import MlflowClient
from services.training_worker.db import get_job, update_status, save_trained_model
from services.training_worker.minio_client import download_dataset, save_model_to_minio

POLL_INTERVAL = 5

logger = logging.getLogger(__name__)


def cleanup_temp_files(dataset_name):
    temp_path = f"/tmp/{dataset_name}"
    csv_path = f"/tmp/{dataset_name}.csv"

    try:
        if os.path.exists(temp_path):
            if os.path.isdir(temp_path):
                shutil.rmtree(temp_path)
            else:
                os.remove(temp_path)

        if os.path.exists(csv_path):
            if os.path.isdir(csv_path):
                shutil.rmtree(csv_path)
            else:
                os.remove(csv_path)

        logger.info(
            "Temporary files cleaned up",
            extra={"event": "cleanup_success", "dataset": dataset_name},
        )
    except Exception as e:
        logger.error(
            f"Cleanup failed: {e}",
            extra={"event": "cleanup_failed", "dataset": dataset_name},
        )


async def worker_loop():
    logger.info("WORKER LOOP STARTED")
    while True:
        try:
            job = await get_job()

            if job:
                logger.info(
                    "Job found, starting processing",
                    extra={
                        "event": "job_polled",
                        "job_id": job.get("job_id"),
                        "dataset_id": job.get("dataset_id"),
                    },
                )
                await process_job(job)
        except Exception as e:
            logger.error(
                f"Worker loop critical error: {e}",
                extra={"event": "worker_loop_error"},
                exc_info=True,
            )

        await asyncio.sleep(POLL_INTERVAL)


async def process_job(job):
    job_id = job["job_id"]
    dataset_name = job["dataset_name"]
    dataset_id = job["dataset_id"]

    job_context = {
        "job_id": job_id,
        "dataset_name": dataset_name,
        "dataset_id": dataset_id,
        "pipeline": "first_ml_baseline",
    }

    try:
        data_path = f"/tmp/{dataset_name}"
        os.makedirs("/tmp", exist_ok=True)
        logger.info(
            "Downloading dataset",
            extra={
                **job_context,
                "event": "dataset_download_start",
                "target_path": data_path,
            },
        )
        download_dataset(dataset_name, data_path)
        csv_path = f"{data_path}.csv"
        shutil.move(data_path, csv_path)
        logger.info(
            "Dataset ready for training",
            extra={**job_context, "event": "dataset_ready", "csv_path": csv_path},
        )

        logger.info(
            "Starting training pipeline",
            extra={**job_context, "event": "training_subprocess_start"},
        )
        result = subprocess.run(
            [
                "python",
                "pipelines/first_ml_baseline/train.py",
                "--data",
                csv_path,
                "--job_id",
                str(job_id),
            ],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            logger.info(
                "Pipeline stdout snip",
                extra={**job_context, "stdout": result.stdout[:500]},
            )

        if result.returncode != 0:
            logger.error(
                "Training pipeline failed",
                extra={
                    **job_context,
                    "event": "training_subprocess_failed",
                    "stderr": result.stderr[:1000],
                },
            )
            raise Exception(f"Pipeline failed: {result.stderr}")

        elif result.stderr:
            logger.warning(
                "Pipeline completed with warnings in stderr",
                extra={
                    **job_context,
                    "event": "pipeline_warnings",
                    "stderr": result.stderr[:500],
                },
            )

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
        logger.info(
            "Uploading model to MinIO",
            extra={
                **job_context,
                "event": "minio_upload_start",
                "model_version": model_version,
            },
        )

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
        logger.info(
            "Job completed successfully",
            extra={
                **job_context,
                "event": "job_success",
                "model_version": model_version,
                "metrics": metrics,
            },
        )

    except Exception:
        logger.error(
            "Job processing failed",
            extra={
                **job_context,
                "event": "job_failed",
            },
            exc_info=True,
        )
        try:
            await update_status(job_id, "failed")
        except Exception:
            logger.error(
                "Failed to update job status to failed",
                extra={**job_context, "event": "status_update_error"},
            )
        # DO NOT re-raise the exception. Let the worker continue to the next job.
    finally:
        cleanup_temp_files(dataset_name)
