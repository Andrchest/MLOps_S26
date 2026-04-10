import asyncio
import subprocess
import mlflow
import re
import os
from mlflow.tracking import MlflowClient
from db import get_job, update_status, save_trained_model
from minio_client import download_dataset, save_model_to_minio

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

        # 3. запустить pipeline
        result = subprocess.run(
            [
                "python",
                "pipelines/first_ml_baseline/train.py",
                "--data",
                data_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise Exception(f"Pipeline failed: {result.stderr}")

        stdout = result.stdout

        match = re.search(r"MLflow run logged successfully: (\S+)", stdout)
        if not match:
            raise Exception("run_id not found in pipeline output")

        run_id = match.group(1)

        client = MlflowClient()
        run = client.get_run(run_id)

        params = run.data.params
        metrics = run.data.metrics
        model_name = run.data.params["model_type"]

        model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

        # 6. версия модели
        model_version = f"{job_id}_{dataset_id}_{run_id}"

        model_path = save_model_to_minio(
            model,
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

        # 8. статус
        await update_status(job_id, "succeeded")

    except Exception as e:
        print(e)
        await update_status(job_id, "failed")
